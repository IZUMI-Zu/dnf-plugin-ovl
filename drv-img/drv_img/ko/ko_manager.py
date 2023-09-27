"""This module provides the class to manage and handle kernel objects (ko)."""

import os
from drv_img.utils.logger import logger
import drv_img.utils.run_cmd as run_cmd


class KOManager:
    """
    Class to manage and handle kernel objects (ko).

    The class can check the compatibility of the kernel objects with current
    kernel version and manage their installation.
    """

    def __init__(self, work_dir, ko_list):
        """Initialize with working directory and list of kernel objects."""
        self._work_dir = work_dir
        self._ko_list = ko_list
        self._kernel_version = self.get_kernel_version(work_dir)

    def _process_version_string(self, raw_version):
        """Process kernel version string to get the necessary version."""
        if raw_version is None:
            return None
        return '.'.join(raw_version.strip().split(' ')[0].split('.'))

    def get_kernel_version(self, root_dir):
        """Get the version of the kernel from the given root directory."""
        current_kernel_raw = run_cmd.get_kernel_version_with_chroot(root_dir)
        print("current_kernel_raw: ", current_kernel_raw)
        return self._process_version_string(current_kernel_raw)

    def get_module_vermagic(self, module_path):
        """
        Get the version magic of the module.
        
        Version magic is a string associated with each module that contains information about the 
        kernel version and configuration for which the module is valid.
        """
        module_compatibility_raw = run_cmd.get_module_vermagic(module_path)
        print("module_path: module_compatibility_raw: ", module_path,
              module_compatibility_raw)
        return self._process_version_string(module_compatibility_raw)

    def check_compatibility(self, module_path):
        """Check if the kernel module is compatible with the current kernel version."""
        module_compatibility = self.get_module_vermagic(module_path)
        if module_compatibility is None:
            return False

        if module_compatibility == self._kernel_version:
            return True

        logger.warning(
            f"module {module_path} is not exactly compatible with kernel {self._kernel_version}"
        )
        print(
            f"module {module_path} is not exactly compatible with kernel {self._kernel_version}"
        )
        return module_compatibility.split(
            '.')[:2] == self._kernel_version.split('.')[:2]

    def check_can_install(self):
        """Check which kernel objects in the list can be installed."""
        return [
            ko for ko in self._ko_list if self.check_compatibility(ko) is True
        ]

    def install_ko(self, kernel_module):
        """Install the kernel module to target directory if it's compatible."""
        if not self.check_compatibility(kernel_module):
            return False

        destination = f"{self._work_dir}/lib/modules/{self._kernel_version}/updates/"
        run_cmd.cp_file(kernel_module, destination)

        run_cmd.depmod(self._work_dir, self._kernel_version)

        ko_base = os.path.basename(kernel_module).split('.')[0]
        run_cmd.modprobe(self._kernel_version, self._work_dir, ko_base)

        return True

    def install_all_ko(self):
        """Install all compatible kernel objects in the list."""
        _to_install = self.check_can_install()
        for ko in _to_install:
            print(f"Installing {ko} to {self._work_dir}")
            if not self.install_ko(ko):
                logger.error(
                    f"Install ko package {ko} to {self._work_dir} failed!")
                raise Exception(
                    f"Install ko package {ko} to {self._work_dir} failed!")
        return True
