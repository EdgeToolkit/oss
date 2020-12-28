#https://docs.conan.io/en/latest/reference/hooks.html
import os


def pre_export(output, conanfile, conanfile_path, **kwargs):
    storage_path = os.getenv('CONAN_STORAGE_PATH')
    if not conanfile.in_local_cache or not storage_path:
        return
    reference = kwargs["reference"]
    rootpath = os.path.join(storage_path, reference.dir_repr())
    filename = os.path.join(rootpath, 'dirty')
    if not os.path.exists(filename):
        from conans.tools import mkdir
        mkdir(rootpath)
        f = open(filename, 'w')
        f.close()
        