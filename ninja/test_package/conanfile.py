from conans import ConanFile
import os

from epm.tools.conan import MetaClass
ConanFile = MetaClass(ConanFile, test_package=True)

class TestPackage(ConanFile):

    def test(self):
        self.run("ninja --version", run_environment=True)
