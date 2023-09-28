"""This module is used to rebuild iso with driver."""

import os
import sys
from tempfile import TemporaryDirectory

from drv_img.kickstart.kickstart_manager import KickManager, KS_PATH
from drv_img.ko.ko_manager import KOManager
from drv_img.rpm.rpm_manager import RpmManager
from drv_img.utils.logger import logger
from drv_img.utils import run_cmd
from drv_img.core.oetype import ArchType
from drv_img.core.global_config import GlobalConfig


class RebuildISOWithDriver:
    """Replace the packages/kernel modules in the given ISO and rebuild the ISO."""
    def __init__(self,
                 iso: str,
                 rpm_path: str,
                 ko_path: str,
                 work_dir: str,
                 output: str,
                 arch: ArchType,
                 mount_point="/root/tmp"):
        self._iso = iso
        self._rpm_path = rpm_path
        self._ko_path = ko_path
        self._work_dir = work_dir
        self._output = output
        self._arch = arch
        self._mount_point = mount_point
        self._to_install_rpm = []
        self._to_install_ko = []
        self._product_name = ""

    def do_iso_rebuild(self):
        """
        Main function to do ISO rebuild.

        :return: None
        """
        self.mount_and_cp()
        self.read_product_name()
        self.inject_driver()
        self.create_repo_group()
        self.make_iso()
        self.implant_iso_md5()

    def mount_and_cp(self):
        """
        This method mounts an ISO file and copies all its contents to a specified directory.
        If any of the steps fail, an error message is logged and printed, and the program exits.

        :raises OSError: If there is an error during the execution of any of the steps.
        """
        print("We are mounting iso, and copy all files, please wait...", )
        logger.info("begin mount iso and copy files")
        iso_mount_path = os.path.join(self._mount_point, "iso_")
        try:
            with TemporaryDirectory(prefix=iso_mount_path,
                                    dir=self._mount_point) as iso_dir:
                if run_cmd.mount(self._iso, iso_dir, "iso9660", "loop"):
                    error_message = f"Failed to mount {self._iso} to {iso_dir}"
                    logger.error(error_message)
                    print(error_message)
                    sys.exit(0)
                logger.info("ISO mounted on dir: %s", iso_dir)

                if run_cmd.cp_iso_file(iso_dir, self._work_dir):
                    error_message = "Failed to cp iso file from {iso_dir} to {self._work_dir}"
                    logger.error(error_message)
                    print(error_message)
                    sys.exit(0)
                logger.info("CP all iso files successfully!")

                if run_cmd.umount(iso_dir):
                    error_message = f"Failed to umount dir {iso_dir}"
                    logger.error(error_message)
                    print(error_message)
                    sys.exit(0)
                logger.info("umount iso successfully")
                logger.info("Mount iso and copy file successfully!")
        except OSError as err:
            logger.error(err)
            print(err)
            sys.exit(0)

    def replace_install_img(self):
        """
        This method replaces the install image in a specified directory with a new one.
        If any of the steps fail, an error message is logged and printed, and the program exits.

        :raises OSError: If there is an error during the execution of any of the steps.
        """
        # unsquashfs
        install_img_path = self._work_dir + "/images/install.img"
        install_mount_path = os.path.join(self._mount_point, "install_")
        squashfs_path = self._work_dir + "/images/squashfs-root"
        rootfs_path = squashfs_path + "/LiveOS/rootfs.img"
        if run_cmd.unsquashfs(install_img_path, squashfs_path) != 0:
            error_message = f"Unsquashfs image Failed! image path: {install_img_path}"
            logger.error(error_message)
            print(error_message)
            sys.exit(0)
        logger.info("Unsquashfs successfully!")
        # mount
        with TemporaryDirectory(prefix=install_mount_path,
                                dir=self._mount_point) as install_dir:
            if run_cmd.mount(rootfs_path, install_dir, "ext4", "rw") != 0:
                logger.error("Failed to mount %s to %s", rootfs_path,
                             install_dir)
                sys.exit(0)
            logger.info("install.img mounted on dir %s", install_dir)

            # install rpm package
            if self._rpm_path:
                print("We are installing rpm package, please wait...")
                self.check_rpm_dependence(install_dir)
                for rpm_pkgs in self._to_install_rpm:
                    if run_cmd.rpm_setup(rpm_pkgs, install_dir) != 0:
                        logger.error("Set up rpm package %s to %s failed!",
                                     rpm_pkgs, install_dir)
                        sys.exit(0)
                    print(f"Set up rpm package {rpm_pkgs} successfully!")
                    logger.info("Set up rpm package %s successfully!",
                                rpm_pkgs)

            # install kernel module
            if self._ko_path:
                print("We are installing ko package, please wait...")
                self._to_install_ko = self.load_ko_list()
                ko_manager = KOManager(install_dir, self._to_install_ko)
                if ko_manager.install_all_ko():
                    logger.info("Install ko package successfully!")
                else:
                    logger.error("Install ko package failed!")
                    sys.exit(0)

            print("Modify kickstart file, please wait...")
            kickstart_manager = KickManager(install_dir, self._to_install_rpm,
                                            self._to_install_ko)
            kickstart_manager.move_driver()
            kickstart_manager.modify_kickstart(install_dir + KS_PATH,
                                               install_dir + KS_PATH)

            # umount + squashfs
            if run_cmd.umount(install_dir) != 0:
                logger.error("Umount %s Failed!", install_dir)
                sys.exit(0)
            if run_cmd.mksquashfs(squashfs_path, install_img_path) != 0:
                logger.error("mksquashfs %s Failed!", squashfs_path)
                sys.exit(0)
        # delete
        if run_cmd.remove_file(squashfs_path) != 0:
            logger.error("Remove file %s failed!", squashfs_path)
            sys.exit(0)

    def read_product_name(self):
        """
        This method reads the product name and version from a .treeinfo file.

        :raises IOError: If there is an error opening or reading the .treeinfo file.
        """
        tree_info_file = os.path.join(self._work_dir, ".treeinfo")
        with open(tree_info_file, encoding='utf-8') as tree_info:
            for content in tree_info:
                if content.startswith("name"):
                    self._product_name = content.split("=")[1].strip()
                    logger.info("product name is %s", self._product_name)
                if content.startswith("version"):
                    GlobalConfig.VERSION_ID = content.split("=")[1].strip()

    def create_repo_group(self):
        """
        This method creates a repository group in the working directory.

        :raises SystemExit: If there is an error during the execution of the 
                            `createrepo_group` function.
        """
        if run_cmd.createrepo_group(self._work_dir) != 0:
            logger.error("Failed to createrepo for dir: %s", self._work_dir)
            sys.exit(0)
        logger.info("createrepo for new iso successfully!")

    def make_iso(self):
        """
        This method creates an ISO file from the contents of the working directory.

        :raises SystemExit: If there is an error during the execution of the `mkisofs` 
                            function or if the product name is not available.
        """
        if self._product_name == "":
            logger.error("failed to get product name!")
            print("failed to get product name! has .treeinfo in iso?")
            sys.exit(0)
        vid = self._product_name + "-" + self._arch.value
        if run_cmd.mkisofs(self._work_dir, self._output, self._arch, vid) != 0:
            logger.error("Failed to rebuild iso")
            sys.exit(0)
        logger.info("ISO rebuild successfully, please check: %s", self._output)

    def replace_repo(self):
        """
        This method replaces the repository in the working directory with a new one.

        :raises SystemExit: If there is an error during the execution of the `cp_file` function.
        """
        new_repo_path = self._work_dir + "/Packages"
        for root, _, files in os.walk(self._rpm_path):
            for file in files:
                src_file = os.path.join(root, file)
                if src_file.endswith(".rpm") is False:
                    continue
                dest_file = os.path.join(new_repo_path, file)
                if run_cmd.cp_file(src_file, dest_file) != 0:
                    logger.error("Copy file %s to %s Failed", src_file,
                                 dest_file)
                    sys.exit(0)

    def inject_driver(self):
        """
        This method injects drivers into the working directory.

        The method performs the following steps:
        1. Logs and prints a message indicating the start of the driver injection process.
        2. Calls the `replace_install_img` method to replace the install image 
            in the working directory.
        3. Calls the `replace_repo` method to replace the repository in the working directory.
        4. Logs a success message indicating the successful completion of driver injection.

        :raises SystemExit: If there is an error during the execution of the
                            `replace_install_img` or `replace_repo` methods.
        """
        logger.info("begin inject drivers")
        print("begin inject drivers, please wait...")
        self.replace_install_img()
        self.replace_repo()
        logger.info("Replace drivers for new iso successfully!")

    def implant_iso_md5(self):
        """
        This method implants the ISO MD5 hash into the output.

        It first calls the `implant_iso_md5` method from the `run_cmd` module on the instance's
            output attribute.
        If the method call is unsuccessful, it logs an error message and exits the program.
        If the method call is successful, it logs a success message.

        Raises:
            SystemExit: If the `implant_iso_md5` method from the `run_cmd` module fails.

        """
        if run_cmd.implant_iso_md5(self._output) != 0:
            logger.error("Implant iso md5 Failed!")
            sys.exit(0)
        logger.info("implant iso md5 successfully!")

    def check_rpm_dependence(self, install_dir):
        """
        This method checks the RPM dependencies for a given installation directory.

        It first creates an instance of the `RpmManager` with the provided installation directory.
        Then it checks if the RPM packages can be installed by calling the `can_install` method 
        on the `RpmManager` instance with the loaded RPM list.

        The method also logs information about each RPM package that will be installed.

        Args:
            install_dir (str): The directory where the RPM packages are to be installed.

        Returns:
            bool: True if the RPM packages can be installed, False otherwise.
        """
        rpm_manager = RpmManager(install_dir)
        installable, _ = rpm_manager.can_install(self.load_rpm_list())

        self._to_install_rpm = [rpm[0] for rpm in installable]

        for rpm_pkg in installable:
            logger.info("rpm package %s will be installed", rpm_pkg)

        return installable is not None

    def load_rpm_list(self):
        """
        This method loads the list of RPM files from the RPM path.

        Returns:
            list: A list of paths to all the RPM files in the RPM path.
        """
        rpm_list = []

        for filename in os.listdir(self._rpm_path):
            if filename.endswith(".rpm"):
                rpm_list.append(os.path.join(self._rpm_path, filename))

        return rpm_list

    def load_ko_list(self):
        """
        This method loads the list of KO files from the KO path.

        Returns:
            list: A list of paths to all the KO files in the KO path.
        """
        ko_list = []

        for filename in os.listdir(self._ko_path):
            if filename.endswith(".ko"):
                ko_list.append(os.path.join(self._ko_path, filename))

        return ko_list
