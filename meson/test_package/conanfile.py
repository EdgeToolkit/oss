from conans import ConanFile, Meson, tools
import os
from epm.tools.conan import as_program
ConanFile = as_program(ConanFile)

class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "pkg_config"

    def build(self):
        meson = Meson(self)
        meson.configure(build_folder="build")
        meson.build()
        self.test()

    def test(self):
        bin_path = os.path.join("build", "test_package")
        self.run(bin_path, run_environment=True)

        self.run("meson --version")

