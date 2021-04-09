from conans import ConanFile
import os

from epm.tools.conan import as_program
ConanFile = as_program(ConanFile)

class TestPackage(ConanFile):

    def test(self):
        self.run("ninja --version", run_environment=True)
