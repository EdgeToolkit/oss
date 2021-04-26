from conans import ConanFile, CMake, tools
import os
from epm.tools.conan import as_test, append_test
ConanFile = as_test(ConanFile)

class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "cmake"
    @append_test
    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        self.run("win_flex --version", run_environment=True)
        self.run("win_bison --version", run_environment=True)

        if not tools.cross_building(self.settings):
            self.run(os.path.join("bin", "bison_test_package"), run_environment=True)
            self.run("{} {}".format(os.path.join("bin", "flex_test_package"), os.path.join(self.source_folder, "basic_nr.txt")), run_environment=True)
