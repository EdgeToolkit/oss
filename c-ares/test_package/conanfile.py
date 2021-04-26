from conans import ConanFile, CMake, tools
import os
from epm.tools.conan import as_test, append_test
ConanFile = as_test(ConanFile)


class CAresTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "cmake", "cmake_find_package"
    @append_test
    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not tools.cross_building(self.settings):
            bin_path = os.path.join("bin", "example")
            self.run(bin_path, run_environment=True)
