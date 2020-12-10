from conans import ConanFile, CMake, tools
import os
from epm.tools.conan import MetaClass
ConanFile = MetaClass(ConanFile, test_package=True)

class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "cmake"

    def build_requirements(self):
        self.build_requires(f're2c/{self.version}')

    def build(self):
        if not tools.cross_building(self.settings):
            cmake = CMake(self)
            cmake.configure()
            cmake.build()

    def test(self):
        if not tools.cross_building(self.settings):
            bin_path = os.path.join("bin", "test_package")
            self.run(bin_path, run_environment=True)
