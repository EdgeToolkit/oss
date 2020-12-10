from conans import ConanFile, CMake, RunEnvironment, tools
import os
from epm.tools.conan import MetaClass
ConanFile = MetaClass(ConanFile, test_package=True)

class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "cmake", "cmake_find_package_multi"

    def build_requirements(self):
        if tools.cross_building(self.settings, skip_x64_x86=True):
            self.build_requires(f"protoc/{self.version}")

    def build(self):
        env_vars = {}
        if not tools.cross_building(self.settings, skip_x64_x86=True):
            rootpath = self.deps_cpp_info['protobuf'].rootpath
            sep = ':' if self.settings.os == 'Linux' else ';'
            env_vars = {"PATH": "{}{}{}".format(
                os.path.join(rootpath, 'bin'),sep, os.environ['PATH'])}
        with tools.environment_append(env_vars):
            self._build()

    def _build(self):        
        cmake = CMake(self)
        cmake.definitions["protobuf_LITE"] = self.options["protobuf"].lite
        cmake.configure()
        cmake.build()

    def test(self):
        if not tools.cross_building(self.settings):
            self.run("protoc --version", run_environment=True)

            self.run(os.path.join("bin", "test_package"), run_environment=True)
