from conans import ConanFile, CMake, tools
import os
from epm.tools.conan import as_test
ConanFile = as_test(ConanFile)

class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "cmake"

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        self.run(os.path.join("bin", "test_package"), run_environment=True)

