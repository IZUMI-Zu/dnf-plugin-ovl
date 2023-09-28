# -*- coding:utf-8 -*-
#
# util.py - generic install utility functions
#
# Copyright (C) 1999-2014
# Red Hat, Inc.  All rights reserved.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
import os
import os.path
import subprocess
from drv_img.core.oetype import ArchType
from drv_img.core.global_config import GlobalConfig
from drv_img.utils.logger import logger

NO_SUCH_PROGRAM = 127


def start_program(argv,
                  root='/',
                  stdin=None,
                  stdout=subprocess.PIPE,
                  stderr=subprocess.STDOUT,
                  **kwargs):
    logger.warning("Running... %s", argv)
    if os.path.isdir(root):
        os.chdir(root)
    return subprocess.Popen(argv,
                            stdin=stdin,
                            stdout=stdout,
                            stderr=stderr,
                            close_fds=True,
                            cwd=root,
                            **kwargs)


def _run_program(argv,
                 root='/',
                 stdin=None,
                 stdout=None,
                 log_output=True,
                 binary_output=False,
                 filter_stderr=False):
    try:
        if filter_stderr:
            stderr = subprocess.PIPE
        else:
            stderr = subprocess.STDOUT

        proc = start_program(argv,
                             root=root,
                             stdin=stdin,
                             stdout=subprocess.PIPE,
                             stderr=stderr)

        (output_string, err_string) = proc.communicate()
        if not binary_output:
            output_string = output_string.decode("utf-8")
            if output_string and output_string[-1] != "\n":
                output_string = output_string + "\n"

        if log_output:
            if binary_output:
                # try to decode as utf-8 and replace all undecodable data by
                # "safe" printable representations when logger binary output
                decoded_output_lines = output_string.decode("utf-8", "replace")
            else:
                # output_string should already be a Unicode string
                decoded_output_lines = output_string.splitlines(True)

            for line in decoded_output_lines:
                logger.info(line.strip())

        if stdout:
            stdout.write(output_string)

        # If stderr was filtered, log it separately
        if filter_stderr and err_string and log_output:
            # try to decode as utf-8 and replace all undecodable data by
            # "safe" printable representations when logger binary output
            decoded_err_string = err_string.decode("utf-8", "replace")
            err_lines = decoded_err_string.splitlines(True)

            for line in err_lines:
                logger.warning(line.strip())

    except OSError as e:
        logger.error("Error running %s: %s", argv[0], e.strerror)
        raise

    logger.debug("Return code: %d", proc.returncode)

    return proc.returncode, output_string


def exec_readlines(command,
                   argv,
                   stdin=None,
                   root='/',
                   env_prune=None,
                   filter_stderr=False):
    class ExecLineReader(object):
        """Iterator class for returning lines from a process and cleaning
           up the process when the output is no longer needed.
        """
        def __init__(self, proc, argv):
            self._proc = proc
            self._argv = argv

        def __iter__(self):
            return self

        def __del__(self):
            # See if the process is still running
            if self._proc.poll() is None:
                # Stop the process and ignore any problems that might arise
                try:
                    self._proc.terminate()
                except OSError:
                    pass

        def __next__(self):
            # Read the next line, blocking if a line is not yet available
            line = self._proc.stdout.readline().decode("utf-8")
            if line == '':
                # Output finished, wait for the process to end
                self._proc.communicate()

                # Check for successful exit
                if self._proc.returncode < 0:
                    raise OSError("process '%s' was killed by signal %s" %
                                  (self._argv, -self._proc.returncode))
                elif self._proc.returncode > 0:
                    raise OSError("process '%s' exited with status %s" %
                                  (self._argv, self._proc.returncode))
                raise StopIteration

            return line.strip()

    argv = [command] + argv

    if filter_stderr:
        stderr = subprocess.DEVNULL
    else:
        stderr = subprocess.STDOUT

    try:
        proc = start_program(argv, root=root, stdin=stdin, stderr=stderr)
    except OSError as e:
        logger.error("Error running %s: %s", argv[0], e.strerror)
        raise

    return ExecLineReader(proc, argv)


def exec_with_redirect(command,
                       argv,
                       stdin=None,
                       stdout=None,
                       root='/',
                       log_output=True,
                       binary_output=False):
    argv = [command] + argv
    return _run_program(argv,
                        stdin=stdin,
                        stdout=stdout,
                        root=root,
                        log_output=log_output,
                        binary_output=binary_output)


def exec_with_capture(command,
                      argv,
                      stdin=None,
                      root='/',
                      log_output=True,
                      filter_stderr=False):
    argv = [command] + argv
    return _run_program(argv,
                        stdin=stdin,
                        root=root,
                        log_output=log_output,
                        filter_stderr=filter_stderr)[1]


def mkdir_chain(directory):
    """ Make a directory and all of its parents. Don't fail if part or
        of it already exists.

        :param str directory: The directory path to create
    """

    os.makedirs(directory, 0o755, exist_ok=True)


def _run_systemctl(command, service, root="/"):
    """
    Runs 'systemctl command service.service'

    :return: exit status of the systemctl

    """

    args = [command, service]
    if root != "/":
        args += ["--root", root]

    ret = exec_with_redirect("systemctl", args)
    if ret[0] != 0:
        logger.error(ret[1])

    return ret[0]


def start_service(service):
    return _run_systemctl("start", service)


def stop_service(service):
    return _run_systemctl("stop", service)


def restart_service(service):
    return _run_systemctl("restart", service)


def service_running(service):
    ret = _run_systemctl("status", service)

    return ret == 0


def is_service_installed(service, root='/'):
    """Is a systemd service installed in the sysroot?

    :param str service: name of the service to check
    :param str root: path to the sysroot or None to use default sysroot path
    """
    if not service.endswith(".service"):
        service += ".service"

    args = ["list-unit-files", service, "--no-legend"]

    if root != "/":
        args += ["--root", root]

    unit_file = exec_with_capture("systemctl", args)

    return bool(unit_file)


def enable_service(service, root='/'):
    ret = _run_systemctl("enable", service, root=root)

    if ret != 0:
        raise ValueError("Error enabling service %s: %s" % (service, ret))


def disable_service(service, root='/'):
    ret = _run_systemctl("disable", service, root=root)

    if ret != 0:
        logger.warning("Disabling %s failed. It probably doesn't exist",
                       service)


def get_mount_paths(devnode):
    '''given a device node, return a list of all active mountpoints.'''
    devno = os.stat(devnode).st_rdev
    majmin = "%d:%d" % (os.major(devno), os.minor(devno))
    mountinfo = (line.split() for line in open("/proc/self/mountinfo"))
    return [info[4] for info in mountinfo if info[2] == majmin]


def decode_bytes(data):
    """Decode the given bytes.

    Return the given string or a string decoded from the given bytes.

    :param data: bytes or a string
    :return: a string
    """
    if isinstance(data, str):
        return data

    if isinstance(data, bytes):
        return data.decode('utf-8')

    raise ValueError("Unsupported type '{}'.".format(type(data).__name__))


def join_paths(path, *paths):
    if len(paths) == 0:
        return path

    new_paths = []
    for p in paths:
        new_paths.append(p.lstrip(os.path.sep))

    return os.path.join(path, *new_paths)


def get_os_arch():
    try:
        arch = exec_with_capture("uname", ["-m"]).strip()
    except Exception as err:
        logger.error(err)
        return ""
    if arch == ArchType.ARM64.value:
        return ArchType.ARM64
    elif arch == ArchType.X86_64.value:
        return ArchType.X86_64
    else:
        logger.error("platform: %s is not supported", arch)
        return ""


def rpm_src_setup(src_path):
    try:
        ret = exec_with_redirect("rpm", ["-i", src_path])
        if ret[0] != 0:
            logger.error(ret[1])
    except Exception as err:
        logger.error(err)
    return ret[0]


def rpm_src_build_pre(spec_path):
    try:
        ret = exec_with_redirect("rpmbuild", ["-bp", spec_path])
        if ret[0] != 0:
            logger.error(ret[1])
    except Exception as err:
        logger.error(err)
    return ret[0]


def rpm_build(spec_file):
    ret = 0
    try:
        _vendor_args = "_vendor {}".format(GlobalConfig.PRODUCT_NAME)
        ret = exec_with_redirect("rpmbuild",
                                 ["-ba", spec_file, "--define", _vendor_args])
        if ret[0] != 0:
            logger.error(ret[1])
    except Exception as err:
        logger.error(err)
    return ret[0]


def yum_download_install(package):
    ret = 0
    try:
        ret = exec_with_redirect("yumdownloader", [
            "--resolve", "--installroot={}".format(GlobalConfig.CACHED_PATH),
            "--destdir={}".format(GlobalConfig.WORK_DIR + "/Packages"), package
        ])
        if ret[0] != 0:
            logger.error(ret[1])
    except Exception as err:
        logger.error(err)
    return ret[0]


def yum_loacl_install(rpm_path, package_path, install_path):
    ret = 0
    try:
        ret = exec_with_redirect("yum", [
            "localinstall", "--installroot={}".format(install_path),
            "--destdir={}".format(package_path), rpm_path
        ])
        if ret[0] != 0:
            logger.error(ret[1])
    except Exception as err:
        logger.error(err)
    return ret[0]


def unsquashfs(efibootimg, uncompress_path):
    ret = 0
    try:
        ret = exec_with_redirect("unsquashfs",
                                 ["-d", uncompress_path, efibootimg])
        if ret[0] != 0:
            logger.error(ret[1])
    except Exception as err:
        logger.error(err)
    return ret[0]


def mksquashfs(liveos, installimg):
    ret = 0
    try:
        ret = exec_with_redirect(
            "mksquashfs", [liveos, installimg, "-noappend", "-comp", "xz"])
        if ret[0] != 0:
            logger.error(ret[1])
    except Exception as err:
        logger.error(err)
    return ret[0]


def replace_vendor_in_boot():
    pass


def replace_rpms_in_minios(work_dir, rpm_path):
    pass


def replace_rpms_in_repo(work_dir, rpm_path):
    os.chdir(work_dir)
    if not os.path.isdir(rpm_path):
        logger.error("%s is not a valid direcotry!", rpm_path)
        return 1
    else:
        if not rpm_path.endswith('/'):
            rpm_path += "/."
        else:
            rpm_path += "."
    ret = 0
    try:
        ret = exec_with_redirect("cp", ["-f", rpm_path, "Packages/"])
        if ret[0] != 0:
            logger.error(ret[1])
    except Exception as err:
        logger.error(err)
    return ret[0]


def createrepo_group(work_dir):
    ret = 0
    try:
        for line in exec_readlines("createrepo",
                                   ["-g", "repodata/normal.xml", "./"],
                                   root=work_dir):
            logger.warning(line)
    except Exception as err:
        logger.error(err)
        ret = 1
    return ret


def cp_iso_file(src_dir, dst_dir):
    ret = 0
    if not os.path.isdir(src_dir):
        logger.error("%s is not a valid direcotry!", src_dir)
        return 1
    elif not os.path.isdir(dst_dir):
        logger.error("%s is not a valid direcotry!", dst_dir)
        return 1
    else:
        if not src_dir.endswith('/'):
            src_dir += "/."
        else:
            src_dir += "."
    try:
        ret = exec_with_redirect("cp", ["-ar", src_dir, dst_dir])
        if ret[0] != 0:
            logger.error(ret[1])
    except Exception as err:
        logger.error(err)
    return ret[0]


def mount(device, mntpoint, ftype, options=None):
    if not options:
        options = "defaults"
    mntpoint = os.path.normpath(mntpoint)
    if not os.path.isdir(mntpoint):
        os.makedirs(dir, 0o755)
    ret = 0
    try:
        ret = exec_with_redirect(
            "mount", ["-t", ftype, "-o", options, device, mntpoint])
        if ret[0] != 0:
            logger.error(ret[1])
    except Exception as err:
        logger.error(err)
    return ret[0]


def umount(mntpoint):
    ret = 0
    try:
        ret = exec_with_redirect("umount", [mntpoint])
        if ret[0] != 0:
            logger.error(ret[1])
    except Exception as err:
        logger.error(err)
    return ret[0]


def mkisofs(work_dir, output, arch, vid):
    cmd = "mkisofs -R -J -T -r -l -d -joliet-long" \
          " -allow-multidot -allow-leading-dots -no-bak" \
          " -no-emul-boot -e images/efiboot.img"
    x86_options = " -b isolinux/isolinux.bin -c isolinux/boot.cat" \
                  " -boot-load-size 4 -boot-info-table -eltorito-alt-boot"
    if arch == ArchType.X86_64:
        cmd += x86_options
    options = " -V {} -o {} {} ".format(vid, output, work_dir)
    cmd += options
    ret = 0
    try:
        logger.warning(cmd)
        ret = subprocess.check_call(cmd, shell=True)
    except Exception as err:
        logger.error("Failed to mkisofs for %s", vid)
        ret = 1
    return ret


def implant_iso_md5(iso_path):
    try:
        ret = exec_with_redirect("implantisomd5", [iso_path])
        if ret[0] != 0:
            logger.error(ret[1])
    except Exception as err:
        logger.error(err)
    return ret[0]


def get_os_release_value(name, sysroot="/"):
    """Read os-release files and return a value of the specified parameter.

    :param name: a name of the parameter (for example, "VERSION_ID")
    :param sysroot: a path to the system root
    :return: a string with the value of None if nothing found
    """
    # Match the variable assignment (for example, "VERSION_ID=").
    name += "="

    # Search all os-release files in the system root.
    paths = ("/etc/os-release", "/usr/lib/os-release")

    for path in paths:
        try:
            with open(join_paths(sysroot, path), "r") as f:
                for line in f:
                    # Match the current line.
                    if not line.startswith(name):
                        continue

                    # Get the value.
                    value = line[len(name):]

                    # Strip spaces and then quotes.
                    value = value.strip().strip("\"'")
                    return value
        except FileNotFoundError:
            pass

    # No value found.
    logger.debug("%s not found in os-release files", name[:-1])
    return None


def replace(file, old_content, new_content, num=None):
    content = read_file(file)
    if num is None:
        content = content.replace(old_content, new_content)
    else:
        content = content.replace(old_content, new_content, num)
    rewrite_file(file, content)


def read_file(file):
    with open(file, encoding='UTF-8') as f:
        read_all = f.read()
        f.close()

    return read_all


def rewrite_file(file, data):
    with open(file, 'w', encoding='UTF-8') as f:
        f.write(data)
        f.close()


def cp_catalog(src_dir, dst_dir):
    if os.path.exists(dst_dir) is False:
        os.makedirs(dst_dir)
    try:
        ret = exec_with_redirect("cp", ["-rf", src_dir, dst_dir])
        if ret[0] != 0:
            logger.error(ret[1])
    except Exception as err:
        logger.error(err)
    return ret[0]


def cp_file(src_file, dst_file):
    try:
        ret = exec_with_redirect("cp", ["-rf", src_file, dst_file])
        if ret[0] != 0:
            logger.error(ret[1])
    except Exception as err:
        logger.error(err)
    return ret[0]


def depmod(work_dir, kernel_version):
    try:
        ret = exec_with_redirect("depmod",
                                 ['-a', '-b', work_dir, kernel_version])
        if ret[0] != 0:
            logger.error(ret[1])
    except Exception as err:
        logger.error(err)
    return ret[0]


def modprobe(kernel_version, work_dir, ko_base):
    try:
        ret = exec_with_redirect(
            "modprobe", ['-S', kernel_version, '-d', work_dir, ko_base])
        if ret[0] != 0:
            logger.error(ret[1])
    except Exception as err:
        logger.error(err)
    return ret[0]


def get_module_vermagic(module_path):
    try:
        module_comp = exec_with_capture("modinfo",
                                        ["-F", "vermagic", module_path])
        return module_comp
    except Exception as err:
        logger.error(err)
        return ""


def get_kernel_version_with_chroot(root_dir):
    try:
        current_kernel = exec_with_capture("chroot", [root_dir, 'uname', '-r'])
        return current_kernel
    except Exception as err:
        logger.error(err)
        return ""


# def cp_output_rpm(output_path):
#     cp_catalog(macro.RPM_SRC_SETUP_RPMS_PATH + "/noarch", output_path)
#     if GlobalConfig.ARCH == ArchType.X86_64:
#         cp_catalog(macro.RPM_SRC_SETUP_RPMS_PATH + "/x86_64", output_path)
#     elif GlobalConfig.ARCH == ArchType.ARM64:
#         cp_catalog(macro.RPM_SRC_SETUP_RPMS_PATH + "/aarch64", output_path)


def rpm_setup(rpm_path, dst_path='/'):
    try:
        root_path = "--root={}".format(dst_path)
        ret = exec_with_redirect(
            "rpm", ["-ivh", rpm_path, root_path, "--force", "--nodeps"])
        if ret[0] != 0:
            logger.error(ret[1])
    except Exception as err:
        logger.error("rpm set up failed! package path:%s, dst_path: %s, %s",
                     rpm_path, dst_path, err)
    return ret[0]


def rpm_check_dependency(rpm_path):
    try:
        output = exec_with_capture("rpm", ["-qR", rpm_path])
        return output
    except Exception as err:
        logger.error(err)
        return ""


def rpm_query_provides(rpm_path):
    try:
        output = exec_with_capture("rpm", ["-q", "--whatprovides", rpm_path])
        return output
    except Exception as err:
        logger.error(err)
        return ""


def remove_file(target_path):
    try:
        ret = exec_with_redirect("rm", ["-rf", target_path])
        if ret[0] != 0:
            logger.error(ret[1])
    except Exception as err:
        logger.error("rm %s failed! %s", target_path, err)
    return ret[0]


def exist_command(cmd):
    try:
        ret = _run_program([cmd, "--help"])
        if ret[0] == NO_SUCH_PROGRAM:
            return False
        else:
            return True
    except FileNotFoundError as err:
        return False
