# drv-img

## Description

A simple program to inject a driver and package into a Linux iso image. drv-img is a utility program that enables users to inject a driver and package into a Linux ISO image. It may be used in several contexts, such as when building custom Linux distros, provisioning new diver which is not provided in published iso, or injecting patch updates into a previously built image.

## Usage

The primary use case of drv-img is to inject a driver into a Linux ISO file. You can do this using the command line interface.


```
usage: drv-img [-h] --iso ISO [--rpm-path RPM_PATH] [--ko-path KO_PATH] --work-dir WORK_DIR --output OUTPUT [-v]

Inject driver to Linux ISO

optional arguments:
  -h, --help           show this help message and exit
  --iso ISO            ISO file used to rebuild
  --rpm-path RPM_PATH  Directory for RPM path
  --ko-path KO_PATH    Directory for kernel module path
  --work-dir WORK_DIR  Directory for ISO rebuild. It must have enough space to uncompress the whole ISO file
  --output OUTPUT      Directory for rebuilt ISO. It must have enough space to store the whole ISO file
  -v, --version        show program's version number and exit
```


## Options Details

- -h, --help:
    
    Shows the help message and exit

- --iso ISO (Must):
    
    The ISO file on which the operations will be performed. This involves specifying the path to the ISO file which the user wants to modify.

- --rpm-path RPM_PATH:
    
    The path to the directory where the RPM (RPM Package Manager) files are stored. These files are typically used for installing, upgrading, and removing software on Linux.

- --ko-path KO_PATH:
    
    The path to the directory containing the Linux kernel module (*.ko) files. These modules are code that can be loaded and unloaded into the kernel upon demand. They extend the functionality of the kernel without needing to reboot the system.

- --work-dir WORK_DIR (Must):
    
    Specify the working directory where the ISO file will be rebuilt. It's important to note that this directory should have enough space to uncompress the entire ISO file.

- --output OUTPUT (Must):
    
    The location where the rebuilt ISO will be saved. This directory must have sufficient space to store the whole ISO file after it's rebuilt.


## Example

To inject a driver into an ISO file, you might use a command like this:


```
drv-img --iso /path/to/your.iso --rpm-path /path/to/rpms --ko-path /path/to/modules --work-dir /path/to/workdir --output /path/to/output
```

## Authors

* [**BINSHUO ZU**](binshuozu@gmail.com)

## License

This project is licensed under the GPL License - see the [LICENSE](LICENSE) file for details
