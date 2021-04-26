from conans import ConanFile
import os

from epm.tools.conan import as_test
ConanFile = as_test(ConanFile)

class TestPackage(ConanFile):

    def build(self):
        self.run("ninja --version", run_environment=True)
