from conans import ConanFile, tools, AutoToolsBuildEnvironment
from contextlib import contextmanager
import os
from epm.tools.conan import MetaClass, delete
ConanFile = MetaClass(ConanFile)


class IperfConan(ConanFile):
    name = "iperf"
    description = "GNU M4 is an implementation of the traditional Unix macro processor"
    topics = ("conan", "m4", "macro", "macro processor")
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://software.es.net/iperf"
    license = "BSD"
    settings = "os", "arch", "compiler", "build_type"

    _autotools = None
    _source_subfolder = "source_subfolder"
    _build_subfolder = "build_subfolder"

    options = {"fPIC": [True, False], "shared": [True, False]}
    default_options = {"fPIC": True, "shared": False}

    def source(self):
        tools.get(**self.conan_data["sources"][self.version])
        os.rename("iperf-" + self.version, self._source_subfolder)

    def _configure_autotools(self):
        if self._autotools:
            return self._autotools
        conf_args = ['--enable-shared=no']
        self._autotools = AutoToolsBuildEnvironment(self)
        self._autotools.configure(args=conf_args, configure_dir=self._source_subfolder)
        return self._autotools

    @contextmanager
    def _build_context(self):
        env = {}
        with tools.environment_append(env):
            yield

    def build(self):
        with self._build_context():
            autotools = self._configure_autotools()
            autotools.make()

    def package(self):
        self.copy(pattern="COPYING", dst="licenses", src=self._source_subfolder)
        with self._build_context():
            autotools = self._configure_autotools()
            autotools.install()
#        tools.rmdir(os.path.join(self.package_folder, "share"))

    def package_id(self):
        self.info.include_build_settings()

    def package_info(self):
        bin_path = os.path.join(self.package_folder, "bin")
        self.output.info("Appending PATH environment variable: {}".format(bin_path))
        self.env_info.PATH.append(bin_path)

