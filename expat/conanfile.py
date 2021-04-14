from conans import ConanFile, CMake, tools
import os
from epm.tools.conan import as_package
ConanFile = as_package(ConanFile)


class ExpatConan(ConanFile):
    name = "expat"
    description = "Fast streaming XML parser written in C."
    topics = ("conan", "expat", "xml", "parsing")
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://github.com/libexpat/libexpat"
    license = "MIT"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}
    generators = "cmake"
    exports_sources = ["CMakeLists.txt", "patches/*"]
    _source_subfolder = "source_subfolder"
    _build_subfolder = "build_subfolder"

    _cmake = None

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            del self.options.fPIC
        del self.settings.compiler.libcxx
        del self.settings.compiler.cppstd

    def source(self):
        tools.get(**self.conan_data["sources"][self.version])
        extracted_dir = self.name + "-" + self.version
        os.rename(extracted_dir, self._source_subfolder)

    def _configure_cmake(self):
        if self._cmake:
            return self._cmake
        self._cmake = CMake(self)
        if tools.Version(self.version) < "2.2.8":
            self._cmake.definitions["BUILD_doc"] = "Off"
            self._cmake.definitions["BUILD_examples"] =  "Off"
            self._cmake.definitions["BUILD_shared"] = self.options.shared
            self._cmake.definitions["BUILD_tests"] = "Off"
            self._cmake.definitions["BUILD_tools"] = "Off"
        else:
            # These options were renamed in 2.2.8 to be more consistent
            self._cmake.definitions["EXPAT_BUILD_DOCS"] = "Off"
            self._cmake.definitions["EXPAT_BUILD_EXAMPLES"] =  "Off"
            self._cmake.definitions["EXPAT_SHARED_LIBS"] = self.options.shared
            self._cmake.definitions["EXPAT_BUILD_TESTS"] = "Off"
            self._cmake.definitions["EXPAT_BUILD_TOOLS"] = "Off"

        self._cmake.configure(build_folder=self._build_subfolder)
        return self._cmake

    def build(self):
        for patch in self.conan_data.get("patches", {}).get(self.version, []):
            tools.patch(**patch)
        cmake = self._configure_cmake()
        cmake.build()

    def package(self):
        self.copy(pattern="COPYING", dst="licenses", src=self._source_subfolder)
        cmake = self._configure_cmake()
        cmake.install()
        tools.rmdir(os.path.join(self.package_folder, "lib", "pkgconfig"))
        tools.rmdir(os.path.join(self.package_folder, "lib", "cmake"))
        tools.rmdir(os.path.join(self.package_folder, "share"))

    def package_info(self):
        self.cpp_info.names["cmake_find_package"] = "EXPAT"
        self.cpp_info.names["cmake_find_package_multi"] = "expat"
        self.cpp_info.libs = tools.collect_libs(self)
        if not self.options.shared:
            self.cpp_info.defines = ["XML_STATIC"]
