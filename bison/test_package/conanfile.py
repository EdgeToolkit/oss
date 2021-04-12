from conans import ConanFile, CMake, tools
import os

from epm.tools.conan import as_program, delete, append_test
ConanFile = as_program(ConanFile)

class TestPackageConan(ConanFile):
    
    settings = "os", "compiler", "build_type", "arch"
    generators = "cmake"
    @delete
    def build_requirements(self):
        if tools.os_info.is_windows and not tools.get_env("CONAN_BASH_PATH") and \
                tools.os_info.detect_windows_subsystem() != "msys2":
            self.build_requires("msys2/20190524")

    @property
    def _mc_parser_source(self):
        return os.path.join(self.source_folder, "mc_parser.yy")
    @append_test
    def build(self):
        if not tools.cross_building(self.settings, skip_x64_x86=True):
            # verify bison may run
            self.run("bison --version", run_environment=True)
            # verify yacc may run
            self.run("yacc --version", run_environment=True, win_bash=tools.os_info.is_windows)
            # verify bison may preprocess something
            self.run("bison -d {}".format(self._mc_parser_source), run_environment=True)

            # verify CMake integration
            cmake = CMake(self)
            cmake.configure()
            cmake.build()

    def test(self):
        if not tools.cross_building(self.settings, skip_x64_x86=True):
            bin_path = os.path.join("bin", "test_package")
            self.run(bin_path, run_environment=True)

            # verify bison works without M4 environment variables
            with tools.environment_append({"M4": None}):
                self.run("bison -d {}".format(self._mc_parser_source), run_environment=True)

            # verify bison works without BISON_PKGDATADIR and M4 environment variables
            with tools.environment_append({"BISON_PKGDATADIR": None, "M4": None}):
                self.run("bison -d {}".format(self._mc_parser_source), run_environment=True)
