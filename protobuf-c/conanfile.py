from conans import ConanFile, CMake, tools, AutoToolsBuildEnvironment
from conans.errors import ConanException
import os
import re

from epm.tools.conan import as_package
ConanFile = as_package(ConanFile)


class ProtobufcConan(ConanFile):
    license = "https://github.com/protobuf-c/protobuf-c/blob/master/LICENSE"
    url = "https://github.com/protobuf-c/protobuf-c"
    description = "conan package for protobuf-c"
    settings = "os", "compiler", "build_type", "arch"
    generators = "cmake"
    exports_sources = ["CMakeLists.txt", 'cmake/*']

    options = { "shared": [True, False] ,
                "with_protoc": [True, False]
              }
    default_options = {
        "shared": False,
        "with_protoc": False
    }

    _source_subfolder = "source_subfolder"
    _pre_install_folder = '_package'
    
    def config_options(self):
        if self.options.with_protoc:
            if self.settings.compiler == 'gcc' and float(self.settings.compiler.version.value) >= 5.1:
                if self.settings.compiler.libcxx != 'libstdc++11':
                    raise ConanException("You must use the setting compiler.libcxx=libstdc++11")

    def source(self):
        tools.get(**self.conan_data["sources"][self.version])
        os.rename('{}-{}'.format(self.name,self.version), self._source_subfolder)
        import shutil
        for i in ['CMakeLists.txt', 'protobuf-c-config.cmake.in']:
            shutil.copy(os.path.join('cmake', i),
                   os.path.join(self._source_subfolder, i))


    def build(self):
        if self.settings.compiler == 'Visual Studio':
            self._msvc_build()
        else:
            self._gnu_build()

    def _gnu_build(self):
        env_build = AutoToolsBuildEnvironment(self)
        configure_dir = os.path.join(self.source_folder, self._source_subfolder)
        prefix = os.path.join(self.build_folder, self._pre_install_folder)
        args=['--disable-protoc', '--prefix=%s' %prefix]
        if self.options.shared:
           args +=['--enable-shared=yes','--enable-static=no']
        else:
           args +=['--enable-shared=no','--enable-static=yes']
        env_build.configure(configure_dir, args=args)
        env_build.make()
        env_build.install()

    def _msvc_build(self):
        cmake = CMake(self)

        prefix = os.path.join(self.build_folder, self._pre_install_folder)
        cmake.configure()
        cmake.build()
        cmake.install()

    def package(self):
        self.copy("*", dst="lib", src="%s/lib" % self._pre_install_folder, links=True)
        self.copy("*", dst="bin", src="%s/bin" % self._pre_install_folder, links=True)
        self.copy("*", dst="include", src="%s/include" % self._pre_install_folder, links=True)

    def package_info(self):
        self.cpp_info.libs = tools.collect_libs(self)
        self.cpp_info.libs.sort(reverse=True)
        if self.settings.os == "Windows":
            if self.options.shared:
                self.cpp_info.defines = ["PROTOBUF_C_USE_SHARED_LIB"]
