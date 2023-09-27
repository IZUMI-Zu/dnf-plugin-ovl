"""This is file is used to store global settings for the application."""

from drv_img.core.oetype import ArchType


class GlobalConfig(object):
    """
    Storage container for global settings for the application.

    Fields:
    ARCH: A constant indicating the architecture type.
    PRODUCT_NAME: The name of the product.
    VERSION_INFO: Version information about the product.
    VERSION_ID: The ID of the version.
    BASE_ISO_VERSION: The base ISO version for the product.
    CACHED_PATH: The path for cached files.
    WORK_DIR: The directory for performing assembly operations.
    OUTPUT: The final output directory.
    ISO: The ISO file to be used.
    RPM_PATH: The path to the RPM files.
    KERNEL_MODULES_PATH: The path to the kernel modules.
    """

    ARCH = ArchType.X86_64
    PRODUCT_NAME = "openEuler"
    VERSION_INFO = "20.03-LTS"
    VERSION_ID = "20.03"
    BASE_ISO_VERSION = "20.03-LTS-SP1"
    CACHED_PATH = "/root/cache"
    WORK_DIR = "/root/isotemp"
    OUTPUT = "/root/res/xxx.iso"
    # ediso
    ISO = "/root/xxx.iso"
    RPM_PATH = ""
    KERNEL_MODULES_PATH = ""
