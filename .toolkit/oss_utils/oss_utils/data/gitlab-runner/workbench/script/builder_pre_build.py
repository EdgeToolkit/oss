import os
import yaml
import shutil
import utils

    
def Main():
    EPM_WORKBENCH = os.getenv('EPM_WORKBENCH')
    WORKBENCH_DIR = os.path.expanduser(f"~/.epm/.workbench/{EPM_WORKBENCH}")
    with open(f"{WORKBENCH_DIR}/config.yml") as f:
        config = yaml.safe_load(f)
        conan = config.get('conan') or {}
        CONAN_STORAGE_PATH = conan.get('storage')
        CONAN_USER_HOME = conan.get('short_path')
    utils.clear_dirty_packages(CONAN_STORAGE_PATH)
    
if __name__ == '__main__':
    Main()