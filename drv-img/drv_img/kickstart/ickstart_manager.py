import os
from pykickstart.version import makeVersion
from pykickstart.parser import KickstartParser, Script
from pykickstart.constants import KS_SCRIPT_POST


class KickManager:
    """
    A class used to modifying kickstart files

    ...

    Attributes
    ----------
    _ko_list : list
        a list of 'ko' file paths
    _rpm_list : list
        a list of rpm file paths

    Methods
    -------
    modify_kickstart(kck_file, output_file)
        Modifies a kickstart file and outputs to a new file
    """

    def __init__(self, ko_list, rpm_list):
        """
        Parameters
        ----------
        ko_list : list
            The 'ko' files list
        rpm_list : list
            The rpm files list
        """
        self._ko_list = ko_list
        self._rpm_list = rpm_list

    def _add_script_to_section(self,
                               ks_parser,
                               content,
                               inChroot,
                               lineno=0,
                               interp='',
                               traceback=False):
        """Adds a script to kickstart parser"""
        new_script = Script(content,
                            interp=interp,
                            inChroot=inChroot,
                            lineno=lineno,
                            type=KS_SCRIPT_POST)
        ks_parser.handler.scripts.append(new_script)

    def _handle_file_section(self, ks_parser, file_list, temp_dir, type_file,
                             inChroot):
        """Handles file section in kickstart parser"""
        script_content = "\n".join(
            self._get_script_content(type_file, temp_dir, file)
            for file in file_list)

        self._add_script_to_section(ks_parser,
                                    script_content,
                                    inChroot=inChroot)

    @staticmethod
    def _get_script_content(type_file, temp_dir, file):
        """Returns script content for specific file type"""
        if type_file == "rpm":
            return "rpm -ivh {}/{} --nodeps --force\nrm -f {}/{}".format(
                temp_dir, os.path.basename(file), temp_dir,
                os.path.basename(file))
        elif type_file == "ko":
            return "insmod {}/{}\nrm -f {}/{}".format(temp_dir,
                                                      os.path.basename(file),
                                                      temp_dir,
                                                      os.path.basename(file))

    def modify_kickstart(self, kck_file, output_file):
        """Opens a kickstart file, modifies it and writes output to a new file"""
        ks_content = self._read_kickstart_file(kck_file)

        ks_parser = KickstartParser(makeVersion())
        ks_parser.readKickstartFromString(ks_content)

        self._process_file_sections(ks_parser)

        self._write_to_output_file(output_file, ks_parser.handler)

    def _read_kickstart_file(self, kck_file):
        """Reads and returns content of a kickstart file"""
        with open(kck_file, 'r') as ks:
            return ks.read()

    def _process_file_sections(self, ks_parser):
        """Processes file sections in kickstart parser"""
        self._add_create_directory_script(ks_parser)
        self._handle_rpm_and_ko_sections(ks_parser)
        self._add_remove_directory_script(ks_parser)

    def _add_create_directory_script(self, ks_parser):
        """Adds create directory script to section"""
        script_content = "install -m 755 -d /mnt/sysimage/tmp"
        self._add_script_to_section(ks_parser, script_content, inChroot=False)

    def _handle_rpm_and_ko_sections(self, ks_parser):
        """Handles rpm and ko sections in kickstart parser"""
        self._handle_file_section(ks_parser, self._rpm_list, "/ks_tmp", "rpm",
                                  True)
        self._handle_file_section(ks_parser, self._ko_list, "/ks_tmp", "ko",
                                  True)

    def _add_remove_directory_script(self, ks_parser):
        """Adds remove directory script to section"""
        script_content = "rm -rf /mnt/sysimage/tmp"
        self._add_script_to_section(ks_parser, script_content, inChroot=False)

    def _write_to_output_file(self, output_file, handler):
        """Writes to output file"""
        try:
            with open(output_file, 'w') as f:
                f.write(handler.__str__())
        except IOError:
            print(f"Error writing to output file: {output_file}")
