import os
import glob
import shutil
import yaml

def clear_dirty_packages(storage_path=None):
    storage_path = storage_path or os.getenv('CONAN_STORAGE_PATH')
    for filename in glob.glob(f"{storage_path}/*/*/*/*/dirty"):
        rootpath = os.path.dirname(filename)
        # TODO: remove short_path
        for i in ['package', 'export']:
            path = f"{rootpath}/{i}"
            if os.path.exists(path):
                print(f'remove dirty package fodler {path}')
                shutil.rmtree(path)
        os.remove(filename)
        for i in ['metadata.json', 'metadata.json.lock']:
            if os.path.exists(f"{rootpath}/{i}"):
                os.remove(f"{rootpath}/{i}")
        try:
            shutil.rmtree(rootpath)
        except Exception as e:
            print("[WARN]", e)

class Workbench(object):
    def __init__(self, workbench=None):
        self._api = None        
        self.EPM_WORKBENCH = workbench or os.getenv('EPM_WORKBENCH')
        self.WORKBENCH_DIR = os.path.expanduser(f"~/.epm/.workbench/{self.EPM_WORKBENCH}")
        with open(f"{self.WORKBENCH_DIR}/config.yml") as f:
            config = yaml.safe_load(f)
            conan = config.get('conan') or {}
            self.CONAN_STORAGE_PATH = conan.get('storage')
            self.CONAN_USER_HOME = conan.get('short_path')
    @property
    def api(self):
        if self._api is None:
            from epm.api import API
            self._api = API(self.WORKBENCH_DIR)
        return self._api


if __name__ == '__main__':
    clear_dirty_packages()        
