import os
import yaml
import shutil
import glob
from utils import Workbench
from conans.model.info import ConanInfo
from conans.util.files import load

def Main():
    print('WD:', os.getcwd())
    print('JOB_NAME:', os.environ['CI_JOB_NAME'])
    job_name  = os.environ['CI_JOB_NAME']
    name = job_name.split('#')[0]
    print('name=', name)
    workbench = Workbench()
    for folder in ['.conan', '.epm']:
        workbench.api.download({'deps': True,
        'reference': f"{name}/{folder}",
        'exclude': [name]
        })
  
if __name__ == '__main__':
    Main()