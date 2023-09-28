"""
This module is designed to handle RPM (Red Hat Package Manager) file 
operations mainly to manage dependencies, comparing versions and 
checking for installation requirements.
"""

import re
import collections
from packaging import version
import rpm as lib_rpm
from drv_img.utils import run_cmd
from drv_img.utils.logger import logger


class RpmManager:
    """
    The class is designed to handle RPM (Red Hat Package Manager) file operations mainly to
    manage dependencies, comparing versions and checking for installation requirements.

    Attributes:
    -----------
    installed_packages {list } -- A list of packages already installed.
    operators {list} -- Operators used in version comparison operations.

    Methods:
    -----------
    get_installed_packages_from_file(file_path)
        Returns the installed packages retrieving from the file path.
    get_rpm_package(provides_input)
        Returns the rpm package by querying against the provided input.
    get_rpm_dependencies(rpm_package)
        Returns dependencies of the given rpm package.
    compare_versions(installed_version, operator, requirement_version)
        Compares installed version against the requirement version using the provided operator.
    is_satisfied(name, operator, _version)
        Checks if the given package name can be installed with the specified version.
    can_install(rpm_list)
        Returns a tuple with list of packages that can be installed and cannot be installed.
    """
    def __init__(self, work_dir, file_path="/root/lorax-packages.log"):
        self.installed_packages = self.get_installed_packages_from_file(
            work_dir + file_path)
        self.operators = ['>=', '<=', '>', '<', '==', '=']

    def _parse_package_info_from_line(self, line):
        match = re.match(r'(.+)-([^-]+)-(.+)\.((x86_64)|(noarch)|(aarch64))',
                         line.strip())
        if match:
            name, rpm_version, release, arch, _, _, _ = match.groups()
            return {
                'name': name,
                'version': rpm_version,
                "release": release,
                'arch': arch,
            }
        return None

    def _parse_packages(self, lines):
        """
        Extract package information from a list of lines.

        Parameters:
        lines (list): A list of string lines from which package information is to be extracted.

        Returns:
        list: A list of dictionaries each containing the package name, version, release, and arch.
        """
        packages = []
        for line in lines:
            pkg_info = self._parse_package_info_from_line(line)
            if pkg_info is not None:
                packages.append(pkg_info)
        return packages

    def get_installed_packages_from_file(self, file_path):
        """
        Retrieve installed packages information from a given file.

        Parameters:
        file_path (str): Path to the file from which installed packages information is to be read.

        Returns:
        list: A list of dictionaries each containing the installed package name, version, 
              release, and architecture information.
        """
        with open(file_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()
        return self._parse_packages(lines)

    def get_rpm_package(self, provides_input):
        """
        Retrieves rpm package information for a provided input.

        Parameters:
        provides_input (str): The input provided to query rpm.

        Returns:
        list or None: A list of dictionaries each containing rpm package information if found; 
                      Otherwise, None.
        """
        output = run_cmd.rpm_query_provides(provides_input)

        if output is None:
            return None

        lines = output.strip().split('\n')

        return self._parse_packages(lines)

    def _search_operator_version(self, line):
        """
        Searches for an operator and version from a given line string.

        Parameters:
        line (str): The line string from which operator and version is to be identified.

        Returns:
        tuple: A tuple containing three elements (name, operator, version) where 'name' is 
               the string before the operator, 'operator' is the operator found, and 'version'
               is the string after the operator. If no operator is found, the operator and 
               version will be None.
        """
        for operator_symbol in self.operators:
            if operator_symbol in line:
                splitted = line.split(operator_symbol)
                return splitted[0].strip(), operator_symbol, splitted[1].strip(
                )
        return line.strip(), None, None

    def _is_special_dependency(self, dependency_name):
        """
        Checks if a given dependency name is a special dependency.

        Parameters:
        dependency_name (str): The name of the dependency to check.

        Returns:
        bool: True if the dependency name is a special dependency; Otherwise, False.
        """
        return dependency_name.startswith(
            "rpmlib(") or dependency_name.startswith("config(")

    def get_rpm_dependencies(self, rpm_package):
        """
        Retrieve rpm dependencies for a given rpm package.

        Parameters:
        rpm_package (str): The name of the rpm package for which dependencies are to be retrieved.

        Returns:
        dict or None: A dictionary containing the dependencies of the package, 
        if found; Otherwise, None.
        """
        dependencies_result = collections.defaultdict(list)
        # TODO: change it to a better way as it depends on host machine's database
        output = run_cmd.rpm_check_dependency(rpm_package)

        if output is None:
            return None

        dependency_lines = output.split('\n')
        for line in dependency_lines:
            if line:  # ignore empty lines
                if line.startswith('/'):  # ignore lines starting with a '/'
                    continue

                dependency_name, operator, dependency_version = self._search_operator_version(
                    line)

                # ignore special dependencies
                if self._is_special_dependency(dependency_name):
                    continue

                packages = self.get_rpm_package(dependency_name)
                if packages is None:  # if there is an error in getting the package
                    return None
                for package in packages:
                    dependencies_result[package["name"]].append({
                        "dependency_name":
                        package["name"],
                        "operator":
                        operator,
                        "version":
                        dependency_version
                    })

        logger.info("Package %s has dependencies: %s", rpm_package,
                    dependencies_result)

        return dependencies_result

    def compare_versions(self, installed_version, operator,
                         requirement_version):
        """
        Compare the installed_version against the requirement_version using operator.
        :param installed_version: the version string of the installed package
        :param operator: a string, one of "==", ">=", "<=", "<", ">"
        :param requirement_version: the version string of the required package
        :return: True if the requirement is satisfied, False otherwise
        """
        installed_version = version.parse(installed_version)
        requirement_version = version.parse(requirement_version)

        if operator == '>=':
            return installed_version >= requirement_version
        elif operator == '<=':
            return installed_version <= requirement_version
        elif operator == '==':
            return installed_version == requirement_version
        elif operator == '>':
            return installed_version > requirement_version
        elif operator == '<':
            return installed_version < requirement_version
        else:
            raise ValueError("Unsupported operator: " + operator)

    def is_satisfied(self, name, operator, _version):
        """
        Checks if the given package name can meet the version requirement. If there is no 
        version requirement (operator is None), returns True. Otherwise, checks if any 
        installed package with the given name can satisfy the version requirement. 

        Parameters:
        name {str} -- Name of the package.
        operator {str} -- Operator used for version comparison. It can be '>=', '<=', '>', 
                          '<', '==' or None.
        _version {str} -- Version requirement for the package.

        Returns:
        {bool} -- Returns True if there is no version requirement or if any installed 
                  package with the given name can meet the version requirement. Otherwise, 
                  returns False. 
        """
        if operator is None:  # if there is no version requirement, return True
            return True
        for installed_pack in self.installed_packages:
            if installed_pack['name'] == name:
                result = self.compare_versions(installed_pack['version'],
                                               operator, _version)
                if result:
                    return True
        return False

    def can_install(self, rpm_list):
        """
        Function checks if provided RPM files can be installed.
        
        It trying to resolve unsatisfied dependencies.
        Returns tuple with list of installable RPMs and 
        list of RPMs that cannot be installed with their unsatisfied dependencies.
        """
        def get_rpm_info(rpm_path):
            """Helper function to extract information from a RPM file"""
            ts = lib_rpm.TransactionSet()
            with open(rpm_path, 'rb') as rpm_file:
                try:
                    hdr = ts.hdrFromFdno(rpm_file)
                    return {
                        'name': hdr[lib_rpm.RPMTAG_NAME],
                        'version': hdr[lib_rpm.RPMTAG_VERSION],
                        'release': hdr[lib_rpm.RPMTAG_RELEASE],
                        'arch': hdr[lib_rpm.RPMTAG_ARCH],
                    }
                except lib_rpm.error as e:
                    print(f"Error reading RPM header: {e}")

        def is_dependency_satisfied(dependency, installed_rpms):
            """Helper function to check if dependency condition is satisfied with currently installed RPMs"""
            dep_name, operator, version = dependency.split()
            return any(
                self.compare_versions(rpm['version'], operator, version
                                      ) if dep_name == rpm['name'] else False
                for rpm in installed_rpms)

        def check_unsatisfied_dependencies(rpm_dependencies):
            """Helper function to check for unsatisfied dependencies in a given dictionary of RPM dependencies"""
            unsatisfied_deps = []
            for pkg, dependencies in rpm_dependencies.items():
                for dependency in dependencies:
                    if not self.is_satisfied(pkg, dependency['operator'],
                                             dependency['version']):
                        unsatisfied_deps.append(dependency)
            return unsatisfied_deps

        to_install = []
        cannot_install = []

        # Loop through all provided RPMs in the RPM list
        for rpm in rpm_list:
            rpm_dependencies = self.get_rpm_dependencies(rpm)
            if rpm_dependencies is None:
                cannot_install.append((rpm, ['Error in getting dependencies']))
                continue

            # Check for unsatisfied dependencies
            unsatisfied_deps = check_unsatisfied_dependencies(rpm_dependencies)
            (cannot_install if unsatisfied_deps else to_install).append(
                (rpm, unsatisfied_deps))

        # Get information for all installable RPMs
        installed_rpms = [get_rpm_info(rpm) for rpm, _ in to_install]

        for rpm, dependencies in cannot_install.copy():
            if dependencies == ['Error in getting dependencies']:
                continue

            for dependency in dependencies.copy():
                if is_dependency_satisfied(dependency, installed_rpms):
                    dependencies.remove(dependency)

            if not dependencies:
                cannot_install.remove((rpm, dependencies))
                to_install.append((rpm, dependencies))

        # Final return with RPMs that can be installed and those that cannot
        return to_install, cannot_install
