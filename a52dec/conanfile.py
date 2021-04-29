import os
import shutil

from conans.errors import ConanException
from conans import ConanFile, CMake, tools, AutoToolsBuildEnvironment

from epm.tools.conan import as_package
ConanFile = as_package(ConanFile)

#
#class A52decConan(ConanFile):
#    name = "a52dec"
#    version = "0.7.4"
#    description = "a52dec is a test program for liba52. It decodes ATSC A/52 streams, "
#    "and also includes a demultiplexer for mpeg-1 and mpeg-2 program streams"
#    url = "https://github.com/conan-multimedia/a52dec"
#    homepage = "http://liba52.sourceforge.net/"
#    license = "GPLv2Plus"
#    settings = "os", "compiler", "build_type", "arch"
#    options = {"shared": [True, False]}
#    default_options = "shared=True"
#    generators = "cmake"
#
#    source_subfolder = "source_subfolder"
#
#    def source(self):
#        url = 'http://liba52.sourceforge.net/files/{name}-{version}.tar.gz'
#        tools.get(url.format(name =self.name, version =self.version))
#        os.rename( self.name + "-" + self.version, self.source_subfolder)
#
#    def build(self):
#        with tools.chdir(self.source_subfolder):
#            with tools.environment_append({'LIBS' : "-lm"}):
#                self.run("autoreconf -f -i")
#
#                _args = ["--prefix=%s/builddir"%(os.getcwd()), "--with-pic", "--disable-silent-rules", "--enable-introspection"]
#                if self.options.shared:
#                    _args.extend(['--enable-shared=yes','--enable-static=no'])
#                else:
#                    _args.extend(['--enable-shared=no','--enable-static=yes'])
#
#                autotools = AutoToolsBuildEnvironment(self)
#                autotools.fpic = True
#                autotools.configure(args=_args)
#                autotools.make(args=["-j4"])
#                autotools.install()
#
#    def package(self):
#        if tools.os_info.is_linux:
#            with tools.chdir(self.source_subfolder):
#                self.copy("*", src="%s/builddir"%(os.getcwd()))
#
#    def package_info(self):
#        self.cpp_info.libs = tools.collect_libs(self)
        
class A52decConan(ConanFile):
    name = "a52dec"
    url = "https://github.com/edgetoolkit/oss"
    homepage = "http://liba52.sourceforge.net/"
    description = "a52dec is a test program for liba52. It decodes ATSC A/52 streams, " \
                  "and also includes a demultiplexer for mpeg-1 and mpeg-2 program streams"
    license = "GPLv2Plus"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}
    exports_sources = ["patches/**", "CMakeLists.txt"]
    generators = "cmake"
    _cmake = None

    @property
    def _source_subfolder(self):
        return "source_subfolder"

    @property
    def _build_subfolder(self):
        return "build_subfolder"

    def configure(self):
        del self.settings.compiler.libcxx
        del self.settings.compiler.cppstd

    def source(self):
        tools.get(**self.conan_data["sources"][self.version])
        os.rename("{}-{}".format(self.name, self.version), self._source_subfolder)
        self._patch_sources()

    def _patch_sources(self):
        for patch in self.conan_data["patches"][self.version]:
            tools.patch(**patch)
        shutil.copy("patches/CMakeLists.txt", self._source_subfolder)
        shutil.copy("patches/liba52.def", self._source_subfolder)
        
    @property
    def cmake(self):
        if self._cmake is None:
            self._cmake = CMake(self)
        return self._cmake

    def _autotools_build(self):
        with tools.chdir(self._source_subfolder):
            with tools.environment_append({'LIBS' : "-lm"}):
                self.run("autoreconf -f -i")

                _args = ["--prefix=%s/builddir"%(os.getcwd()), "--disable-silent-rules", "--enable-introspection"]
                if self.options.shared:
                    _args.extend(['--enable-shared=yes','--enable-static=no'])
                else:
                    _args.extend(['--enable-shared=no','--enable-static=yes'])
                    

                autotools = AutoToolsBuildEnvironment(self)
                # _args += ["--with-pic"]
                # autotools.fpic = True
                autotools.configure(args=_args)
                autotools.make(args=["-j4"])
                autotools.install()        

    def build(self):
        if tools.os_info.is_linux:
            self._autotools_build()
        else:
            self.cmake.configure(build_folder=self._build_subfolder)
            self.cmake.build()
        
    def package(self):
        if tools.os_info.is_linux:
            with tools.chdir(self._source_subfolder):
                self.copy("*", src="%s/builddir"%(os.getcwd()))
        else:
            self.cmake.install()

    def package_info(self):
        self.cpp_info.libs = tools.collect_libs(self)
