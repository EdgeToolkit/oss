from conans import ConanFile, CMake, tools
from conans.errors import ConanInvalidConfiguration
import os
from epm.tools.conan import as_package
ConanFile = as_package(ConanFile)

class NinjaConan(ConanFile):
    name = "ninja"
    description = "Ninja is a small build system with a focus on speed"
    license = "Apache-2.0"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://github.com/ninja-build/ninja"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = ["CMakeLists.txt", "*.patch"]
    generators = "cmake"
    topics = ("conan", "ninja", "build")

    _source_subfolder = "source_subfolder"
    _cmake = None


    @property
    def _is_msvc(self):
        return self.settings.compiler == "Visual Studio"

    def source(self):
        tools.get(**self.conan_data["sources"][self.version])
        os.rename("ninja-%s" % self.version, self._source_subfolder)

    def build(self):
        with tools.chdir(self._source_subfolder):
            with tools.vcvars(self.settings, filter_known_paths=False) if self._is_msvc else tools.no_op():
                self.run("python configure.py --bootstrap")

    def package(self):
        self.copy(pattern="COPYING", dst="licenses", src=self._source_subfolder)
        self.copy(pattern="ninja*", dst="bin", src=self._source_subfolder)

    def package_id(self):
        del self.info.settings.compiler
        del self.info.settings.build_type

    def package_info(self):
        # ensure ninja is executable
        if str(self.settings.os) in ["Linux", "Macosx"]:
            name = os.path.join(self.package_folder, "bin", "ninja")
            os.chmod(name, os.stat(name).st_mode | 0o111)
        self.env_info.PATH.append(os.path.join(self.package_folder, "bin"))
        self.env_info.CONAN_CMAKE_GENERATOR = "Ninja"

