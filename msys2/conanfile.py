from conans import ConanFile, tools
from conans.errors import ConanInvalidConfiguration
import os
import shutil
from epm.tools.conan import as_package
ConanFile = as_package(ConanFile)


class MSYS2Conan(ConanFile):
    name = "msys2"
    description = "MSYS2 is a software distro and building platform for Windows"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "http://www.msys2.org"
    license = "MSYS license"
    topics = ("conan", "msys", "unix", "subsystem")
    short_paths = True
    options = {"exclude_files": "ANY",  # Comma separated list of file patterns to exclude from the package
               "packages": "ANY",  # Comma separated
               "additional_packages": "ANY"}    # Comma separated
    default_options = {"exclude_files": "*/link.exe",
                       "packages": "base-devel,binutils,gcc",
                       "additional_packages": None}
    settings = "os", "arch"
    
    _bsdtar = None

    def configure(self):
        if self.settings.os != "Windows":
            raise ConanInvalidConfiguration("Only Windows supported")

    def source(self):
        # build tools have to download files in build method when the
        # source files downloaded will be different based on architecture or OS
        pass

    def _download(self, url, sha256):
        from six.moves.urllib.parse import urlparse
        filename = os.path.basename(urlparse(url[0]).path)
        tools.download(url=url, filename=filename, sha256=sha256)
        return filename

    @property
    def _msys_dir(self):
        return "msys64" if self.settings.arch == "x86_64" else "msys32"
    
    @property
    def tar(self):
        ver = '3.5.1'
        url = f'https://github.com/libarchive/libarchive/releases/download/{ver}/libarchive-v{ver}-win64.zip'
        if self._bsdtar is None:
            tools.get(url, destination='.')
            self._bsdtar = os.path.abspath(os.path.join('libarchive', 'bin', 'bsdtar.exe'))
        return self._bsdtar
    
    def _pre_install(self):
        mirror = os.getenv('MSYS2_VERSION_MIRROR')
        if mirror:
            with tools.chdir(os.path.join(self._msys_dir)):
                mirrorlist = os.path.join('etc','pacman.d', 'mirrorlist.msys')
                os.rename(mirrorlist, mirrorlist + '.backup')
                with open(mirrorlist, 'w') as f:
                    f.write(f"Server = {mirror}/{self.version}/$arch/\n")
                    

    def _post_install(self):
        mirror = os.getenv('MSYS2_VERSION_MIRROR')
        if mirror:
            with tools.chdir(os.path.join(self._msys_dir)):
                mirrorlist = os.path.join('etc','pacman.d', 'mirrorlist.msys')
                backup = f"{mirrorlist}.backup"
                if os.path.exists(backup):
                    os.remove(mirrorlist)
                    os.rename(backup, mirrorlist)
        import shutil
        shutil.rmtree(os.path.join(self._msys_dir, 'var', 'cache'))

    def build(self):
        arch = 0 if self.settings.arch == "x86" else 1  # index in the sources list
        filename = self._download(**self.conan_data["sources"][self.version][arch])
        tar_name = filename.replace(".xz", "")
        self.run(f"{self.tar} -vxf {filename}")
        os.unlink(filename)

        packages = []
        if self.options.packages:
            packages.extend(str(self.options.packages).split(","))
        if self.options.additional_packages:
            packages.extend(str(self.options.additional_packages).split(","))

        self._pre_install()

        with tools.chdir(os.path.join(self._msys_dir, "usr", "bin")):            
            for package in packages:
                self.run('bash -l -c "pacman -S %s --noconfirm"' % package)

        # create /tmp dir in order to avoid
        # bash.exe: warning: could not find /tmp, please create!
        tmp_dir = os.path.join(self._msys_dir, 'tmp')
        if not os.path.isdir(tmp_dir):
            os.makedirs(tmp_dir)
        tmp_name = os.path.join(tmp_dir, 'dummy')
        with open(tmp_name, 'a'):
            os.utime(tmp_name, None)

        # Prepend the PKG_CONFIG_PATH environment variable with an eventual PKG_CONFIG_PATH environment variable
        tools.replace_in_file(os.path.join(self._msys_dir, "etc", "profile"),
                              'PKG_CONFIG_PATH="', 'PKG_CONFIG_PATH="$PKG_CONFIG_PATH:')
        
        self._post_install()

    def package(self):
        excludes = None
        if self.options.exclude_files:
            excludes = tuple(str(self.options.exclude_files).split(","))
        self.copy("*", dst="bin", src=self._msys_dir, excludes=excludes)
        shutil.copytree(os.path.join(self.package_folder, "bin", "usr", "share", "licenses"),
                        os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        msys_root = os.path.join(self.package_folder, "bin")
        msys_bin = os.path.join(msys_root, "usr", "bin")

        self.output.info("Creating MSYS_ROOT env var : %s" % msys_root)
        self.env_info.MSYS_ROOT = msys_root

        self.output.info("Creating MSYS_BIN env var : %s" % msys_bin)
        self.env_info.MSYS_BIN = msys_bin

        self.output.info("Appending PATH env var with : " + msys_bin)
        self.env_info.path.append(msys_bin)
