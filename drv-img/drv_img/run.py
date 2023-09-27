"""The main entry point for the drv-img tool."""

#!/bin/python
import argparse
import pathlib
import sys
import os
import shutil
import time
from argparse import RawTextHelpFormatter
from drv_img.utils.run_cmd import get_os_arch
from drv_img.core.global_config import GlobalConfig
from drv_img.utils.logger import logger
from drv_img.rebuild_iso import RebuildISOWithDriver
import drv_img


def init_config(parser: argparse.ArgumentParser):
    """
    Initialize the global configuration.

    Parameters:
        parser (argparse.ArgumentParser): The parser containing configuration data.
    """
    arch = get_os_arch()
    if not arch:
        sys.exit(1)
    GlobalConfig.ARCH = arch
    get_config_parser(parser)


def check_exist_outdir():
    """
    Check if the output directory exists.

    Asserts the location ends in '.iso' and that the directory it would be placed in exists,
    creating it if not.
    """
    if not GlobalConfig.OUTPUT.endswith("iso"):
        logger.error("Please define the --output like /xxx/xxx/xxx.iso")
        sys.exit(0)
    dirname = os.path.dirname(os.path.abspath(GlobalConfig.OUTPUT))
    if not os.path.exists(dirname):
        os.makedirs(dirname)


def check_exist_workdir():
    """
    Check if the work directory exists.

    Asserts the existence of the work directory, and if it doesn't exist, creates it. If the path exists but is not a 
    directory, it logs an error and exits the program.
    """
    work_dir = os.path.abspath(GlobalConfig.WORK_DIR)
    if not os.path.exists(work_dir):
        os.makedirs(work_dir)
    if not os.path.isdir(work_dir):
        logger.error("Work path is not a directory. Path: %s", work_dir)
        sys.exit(0)


def check_exist_ko():
    """
    Check if the kernel modules exist.

    Asserts the existence of the directory for kernel module files (.ko files). 
    Creates it if it doesn't exist. If the path exists but is not a directory, 
    or if no .ko files are found in the directory, logs an error and exits the program.
    """
    ko_path = os.path.abspath(GlobalConfig.KERNEL_MODULES_PATH)
    if not os.path.exists(ko_path):
        os.makedirs(ko_path)
    if not os.path.isdir(ko_path):
        logger.error(
            "Kernel modules path exists, but is not a directory! Path: %s",
            GlobalConfig.KERNEL_MODULES_PATH)
        sys.exit(0)

    # check if there is any .ko file in the directory
    if not any(fname.endswith('.ko') for fname in os.listdir(ko_path)):
        logger.error("Cannot find any .ko file in the directory: %s", ko_path)
        sys.exit(0)


def check_exist_rpm():
    """
    Check if the RPMs exist.

    Asserts the existence of the directory for RPM files. If it doesn't exist, creates it. 
    If the path exists but is not a directory, or if no .rpm files are found in the
    directory, logs an error and exits the program.
    """
    rpm_path = os.path.abspath(GlobalConfig.RPM_PATH)
    if not os.path.exists(rpm_path):
        os.makedirs(rpm_path)
    if not os.path.isdir(rpm_path):
        logger.error("RPMS path exists, but is not a directory! Path: %s",
                     GlobalConfig.RPM_PATH)
        sys.exit(0)

    # check if there is any .rpm file in the directory
    if not any(fname.endswith('.rpm') for fname in os.listdir(rpm_path)):
        logger.error("Cannot find any RPM file in the directory: %s", rpm_path)
        sys.exit(0)


def check_exist_iso():
    """
    Check if the ISO file exists.

    Asserts the existence of the ISO file. If it doesn't exist, 
    logs an error and exits the program.
    """
    if not os.path.exists(os.path.abspath(GlobalConfig.ISO)):
        logger.error("Cannot find the ISO file. Path: %s", GlobalConfig.ISO)
        sys.exit(0)


def get_config_parser(parser):
    """
    Extract configuration from the parser and check paths exist.

    Parameters:
        parser (argparse.ArgumentParser): The parser containing configuration data.
    """
    GlobalConfig.ISO = parser.iso[0]
    GlobalConfig.WORK_DIR = parser.work_dir[0]
    GlobalConfig.OUTPUT = parser.output[0]

    if parser.rpm_path is not None and len(parser.rpm_path) > 0:
        GlobalConfig.RPM_PATH = parser.rpm_path[0]

    if parser.ko_path is not None and len(parser.ko_path) > 0:
        GlobalConfig.KERNEL_MODULES_PATH = parser.ko_path[0]

    check_exist_iso()
    if not GlobalConfig.RPM_PATH == "":
        check_exist_rpm()
    if not GlobalConfig.KERNEL_MODULES_PATH == "":
        check_exist_ko()
    check_exist_workdir()
    check_exist_outdir()


def parse_cli():
    """
    Parse the command-line arguments.

    Returns:
        argparse.Namespace: The parsed arguments.
    """
    parser = argparse.ArgumentParser(description="Inject driver to Linux ISO",
                                     formatter_class=RawTextHelpFormatter)

    # Common arguments
    parser_argument(parser)

    config = parser.parse_args()

    if config.rpm_path is None and config.ko_path is None:
        print("No rpm and ko driver are specified do nothing")
        sys.exit(0)

    if config.rpm_path is None:
        print("No rpm driver are specified do with ko driver")

    if config.ko_path is None:
        print("No ko driver are specified do with rpm driver")

    if not hasattr(config, 'func'):
        parser.print_help()
        sys.exit(0)

    return config


def parser_argument(parser: argparse.ArgumentParser):
    """
    Define the command-line arguments to the parser.

    Parameters:
        parser (argparse.ArgumentParser): The parser to define arguments for.
    """
    parser.add_argument("--iso",
                        required=True,
                        nargs=1,
                        dest="iso",
                        help="ISO file used to rebuild")
    parser.add_argument("--rpm-path",
                        required=False,
                        nargs=1,
                        dest="rpm_path",
                        help="Directory for RPM path")
    parser.add_argument("--ko-path",
                        required=False,
                        nargs=1,
                        dest="ko_path",
                        help="Directory for kernel module path")
    parser.add_argument(
        "--work-dir",
        required=True,
        nargs=1,
        dest="work_dir",
        help="Directory for ISO rebuild. It must have enough space "
        "to uncompress the whole ISO file")
    parser.add_argument(
        "--output",
        required=True,
        nargs=1,
        dest="output",
        help="Directory for rebuilt ISO. It must have enough space "
        "to store the whole ISO file")
    parser.add_argument('-v',
                        '--version',
                        action='version',
                        version="drv-img version: {}\n"
                        "Python version: {}\n"
                        "Execution path: {}\n"
                        "Timestamp: {}".format(drv_img.__version__,
                                               sys.version,
                                               pathlib.Path().absolute(),
                                               time.ctime()))

    parser.set_defaults(func=process_with_replace_driver)


def process_with_replace_driver(parser: argparse.ArgumentParser):
    """
    Replace the packages/kernel modules in the given ISO and rebuild the ISO.

    Parameters:
        parser (argparse.ArgumentParser): The parser containing configuration data.
    """
    init_config(parser)
    iso_rebuilder = RebuildISOWithDriver(GlobalConfig.ISO,
                                         GlobalConfig.RPM_PATH,
                                         GlobalConfig.KERNEL_MODULES_PATH,
                                         GlobalConfig.WORK_DIR,
                                         GlobalConfig.OUTPUT,
                                         GlobalConfig.ARCH)
    iso_rebuilder.do_iso_rebuild()


def clean_work_dir():
    """
    Clean the work directory.

    Removes the global work directory if it exists.
    """
    if os.path.exists(GlobalConfig.WORK_DIR):
        shutil.rmtree(GlobalConfig.WORK_DIR)


def main():
    parser = parse_cli()
    parser.func(parser)
    clean_work_dir()


if __name__ == "__main__":
    main()
