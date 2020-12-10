# -*- coding: utf-8 -*-
import os
from conans import ConanFile
from epm.tools.conan import MetaClass
ConanFile = MetaClass(ConanFile, test_package=True)


class DefaultNameConan(ConanFile):
    settings = "os", "arch"

    def test(self):
        self.run("perl --version")
        perl_script = os.path.join(self.source_folder, "list_files.pl")
        self.run('perl {}'.format(perl_script), run_environment=True)
