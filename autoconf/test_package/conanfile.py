from conans import AutoToolsBuildEnvironment, ConanFile, tools
from contextlib import contextmanager
import os
import shutil
from epm.tools.conan import as_test, delete, append_test
ConanFile = as_test(ConanFile)

class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "configure.ac", "config.h.in", "Makefile.in", "test_package_c.c", "test_package_cpp.cpp",
    @delete
    def build_requirements(self):
        if tools.os_info.is_windows and "CONAN_BASH_PATH" not in os.environ:
            self.build_requires("msys2/20190524")

    @contextmanager
    def _build_context(self):
        if self.settings.compiler == "Visual Studio":
            with tools.vcvars(self.settings):
                with tools.environment_append({"CC": "cl -nologo", "CXX": "cl -nologo",}):
                    yield
        else:
            yield
    @append_test
    def build(self):
        for src in self.exports_sources:
            shutil.copy(os.path.join(self.source_folder, src), self.build_folder)
        self.run("{} --verbose".format(os.environ["AUTOCONF"]), win_bash=tools.os_info.is_windows)
        self.run("{} --help".format(os.path.join(self.build_folder, "configure").replace("\\", "/")), win_bash=tools.os_info.is_windows)
        autotools = AutoToolsBuildEnvironment(self, win_bash=tools.os_info.is_windows)
        with self._build_context():
            autotools.configure()
            autotools.make()

    def test(self):
        if not tools.cross_building(self.settings):
            self.run(os.path.join(".", "test_package"), run_environment=True)
