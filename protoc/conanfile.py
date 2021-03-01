import os
from conans import ConanFile, CMake, tools
from conans.errors import ConanInvalidConfiguration
from conans.tools import Version
from epm.tools.conan import as_package, delete
ConanFile = as_package(ConanFile)

class ProtobufCompilerConan(ConanFile):
    name = "protoc"
    description = "Protocol Buffers Compiler"
    topics = ("conan", "protobuf", "protocol-buffers",
              "protocol-compiler", "serialization", "rpc", "protocol-compiler")
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://github.com/protocolbuffers/protobuf"
    license = "BSD-3-Clause"
    settings = "os", "arch", "compiler", "build_type"


    def configure(self):
        if self.settings.os == "Windows" and self.settings.compiler == "Visual Studio":
            compiler_version = Version(self.settings.compiler.version.value)
            if compiler_version < "14":
                raise ConanInvalidConfiguration("On Windows Protobuf can only be built with "
                                                "Visual Studio 2015 or higher.")
    def build(self):
        pass

    def package(self):
        rootpath = self.deps_cpp_info['protobuf'].rootpath
        
        self.copy("LICENSE", dst="licenses", src=os.path.join(rootpath, "licenses"))
        self.copy("*", dst="bin", src=os.path.join(rootpath, 'bin'))
        self.copy("cmake/*", dst="lib", src=os.path.join(rootpath, 'lib'))

    def package_info(self):
        bindir = os.path.join(self.package_folder, "bin")
        self.output.info("Appending PATH environment variable: {}".format(bindir))
        self.env_info.PATH.append(bindir)
        bin_ext = ".exe" if self.settings.os == "Windows" else ""
        protoc_bin = os.path.join(bindir, "protoc{}".format(bin_ext)).replace("\\", "/")
        self.env_info.PROTOC = protoc_bin

