from conans import ConanFile, tools
from epm.tools.conan import as_program
ConanFile = as_program(ConanFile, test_package=True)

class TestPackage(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    
    def test(self):
        if not tools.cross_building(self.settings):
            self.run("7z.exe")
