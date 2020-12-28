#!/usr/bin/env python3
import os
import yaml
import fnmatch
import gitlab
import platform
import argparse
import shutil
import subprocess
import sqlite3

from jinja2 import Environment, FileSystemLoader
from .lockfile import FileLock

PLATFORM = platform.system()
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')

def abspath(path):
    return os.path.abspath(os.path.expanduser(path))

def load_config(path):
    path = os.path.abspath(os.path.expanduser(path))
    with open(path) as f:
        config = yaml.safe_load(f)
        config['__file__'] = path

    conan = config.pop('conan', None) or {}    
    username = conan.pop('username', None)
    password = conan.pop('password', None)
    for name, conf in conan['remote'].items():
        conf['name'] = name
        conf['username'] = conf.get('username') or username
        conf['password'] = conf.get('password') or password
    
    workbench = config.pop('workbench', None) or {}
    for name in workbench:
        wb = workbench[name] or {}
        repos = [conan['remote'][name]]
        for i in wb.get('conan') or []:
            if i != name:
                repos.append(conan['remote'][i])
        wb['conan'] = repos
        workbench[name] = wb

    config['gitlab'] = dict({'group':None}, **config['gitlab'])
    config['workbench'] = workbench
    config['conan'] = conan
    
    return config

class HashTable(object):

    def __init__(self, filename):
        self.filename = os.path.abspath(os.path.expanduser(filename))

    def _load(self):
        if os.path.exists(self.filename):
            with open(self.filename) as f:
                return yaml.safe_load(f) or {}
        return {}

    def _dump(self, data):
        path = os.path.dirname(self.filename)
        if not os.path.exists(path):
            os.makedirs(path)
        with open(self.filename, 'w') as f:
            yaml.safe_dump(data, f, default_flow_style=False)

    @property
    def item(self):
        with FileLock(self.filename):
            return self._load()

    def get(self, id):
        return self.item.get(id)

    def remove(self, id):
        with FileLock(self.filename):
            data = self._load()
            if id in data:
                del data[id]
                self._dump(data)

    def update(self, id, value):
        with FileLock(self.filename):
            data = self._load()
            data[id] = value
            self._dump(data)

class GitlabRunner(object):

    def __init__(self, hostname, type, workbench, device_hostname=None, gitlab=None, db=None):
        """Gitlab runner property object

        Args:
            hostname (str): hostname where the runner to be deployed
            type (str): builder,runner,deployer
            workbench (str): workbench that is related working enviroment and configs
            device_hostname (str): revered , None for now
            format $hostname/$type/$workbench[->$device_hostname]
        """

        self.hostname = hostname
        self.type = type
        self.workbench = workbench
        self.device_hostname = device_hostname
        self._gitlab = gitlab
        self._db = db
        
    @property
    def name(self):
        name = f"{self.hostname}/{self.type}/{self.workbench}" 
        return f"{name}->{self.device_hostname}" if self.device_hostname else name

    def register(self, register_token, tag=[]):
        assert self._gitlab and self._db
        print('================>>', self.name)
        runner = self.runner
        if runner is None:
         
            runner = self._gitlab.runners.create({'token': register_token,
                                      'description': self.name,
                                      'tag_list': tag,
                                      'info': {'name': self.name}
                                      })
            self._db.update(runner.id, {'token': runner.token, 'name': self.name})            
        return runner

    def unregister(self):
        runner = self.runner
        if runner:
            self._db.remove(runner.id)
            runner.delete()
            
        return runner
    
    @property
    def runner(self):
        for runner in self._gitlab.runners.list():
            if self.name ==  runner.name:
                return runner
        return None

    @staticmethod
    def load(name, gitlab=None, db=None):
        section = name.split('->')
        hostname, type, workbench = section[0].split('/')
        device = section[1] if len(section) > 1 else None
        return GitlabRunner(hostname, type, workbench, device, gitlab=gitlab, db=db)



class GitlabRunnerManager(object):
    

    def __init__(self, config, db=None):
        self.config = config
        if isinstance(self.config, str):
            self.config = load_config(self.config)
        self.db = db
        if isinstance(self.db, str):
            self.db = HashTable(self.db)
        self._gitlab = None

    @property
    def gitlab(self):
        if self._gitlab is None:
            url = self.config['gitlab']['url']
            private_token = self.config['gitlab']['private_token']
            self._gitlab = gitlab.Gitlab(url, private_token=private_token)
        return self._gitlab


    def register(self, hostname, type, platform=None):
        types = [type] if isinstance(type, str) else type
        register_token = self.config['gitlab']['register_token']
        platform = platform or PLATFORM
        result = []
        for workbench in self.config['workbench']:
            for runner_type in types:
                tags = [f"{workbench}@workbench"]
                tags += self.config['tag'][platform][runner_type] 
                

                cli = GitlabRunner(hostname, type, workbench=workbench,gitlab=self.gitlab, db=self.db)
                runner = cli.register(register_token, tags)
                result.append(runner)
        return result


    def unregister(self, hostname, type=None):
        result = []
        for runner in self.gitlab.runners.list():
            if runner.name and isinstance(runner.name, str):
                r = GitlabRunner.load(runner.name)
                if r.hostname != hostname:
                    continue
                # TODO: more confition
                
                runner.delete() 
                if self.db:
                    self.db.remove(runner.id)
                result.append(runner)
        return result

    def generate(self, hostname, type, platform, home, out_dir=None):

        out_dir = abspath(out_dir or f"./tmp/gitlab-runner/{hostname}")
        types = [type] if isinstance(type, str) else type
        register_token = self.config['gitlab']['register_token']
        platform = platform or PLATFORM
        result = []
        content =  ""
        for workbench in self.config['workbench']:
            for rtype in types:                
                cli = GitlabRunner(hostname, rtype, workbench=workbench, gitlab=self.gitlab, db=self.db)
                runner = cli.runner
                if not runner:
                    raise Exception(f'can not get {cli.name} runner')
                id = runner.id
                item = self.db.get(id)
                if not item:
                    raise Exception(f'{id} not found in hash table')
                token = item['token']
                url = self.config['gitlab']['url']
                template = self._template(f"{rtype}.toml.j2")
                content += template.render(platform=platform, token=token, id=id, url=url, HOME=home, workbench=workbench,
                hostname=hostname)
        if os.path.exists(out_dir):
            shutil.rmtree(out_dir)
        os.makedirs(out_dir)
        with open(os.path.join(out_dir, 'config.toml'), 'w') as f:
            f.write(content)

        template_dir = os.path.join(DATA_DIR, 'gitlab-runner', 'workbench')

        for workbench in self.config['workbench']:
            for rtype in types:
                dst_dir = f"{out_dir}/workbench/{workbench}/{rtype}"
                os.makedirs(os.path.join(dst_dir))
                shutil.copytree(os.path.join(template_dir, 'script'), os.path.join(dst_dir, 'script'))

                hooks_dir = f"{dst_dir}/.conan/hooks"
                os.makedirs(hooks_dir)
                shutil.copy(os.path.join(template_dir, f'conan/hooks/{rtype}.py'), 
                    os.path.join(f'{hooks_dir}/{rtype}.py'))
                # generate conan files
                os.environ['CONAN_USER_HOME'] = os.path.abspath(dst_dir)
                subprocess.run(['conan', 'remote', 'clean'], check=True)
                if rtype == 'deployer':
                    os.environ['CONAN_REVISIONS_ENABLED'] = '1'
                    for remote in self.config['workbench'][workbench]['conan'] or []:
                        if remote['name'] != workbench:
                            continue
                        # conan remote add remote url False
                        subprocess.run(['conan', 'remote', 'add', remote['name'], remote['url'], 'False'], check=True)

                        # conan user -p password -r remote remote username
                        subprocess.run(['conan', 'user', '-r', remote['name'], '-p', remote['password'], remote['username']], 
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                        check=True)
                        break
                else:
                    for remote in self.config['workbench'][workbench]['conan'] or []:
                        # conan remote add remote url False
                        subprocess.run(['conan', 'remote', 'add', remote['name'], remote['url'], 'False'], check=True)
        

    @staticmethod
    def _template(filename):
        path = os.path.join(DATA_DIR, 'gitlab-runner')
        env = Environment(loader=FileSystemLoader(path))
        env.trim_blocks = True
        template_file = os.path.basename(filename)
        return env.get_template(template_file)

# gitlab_runner.py register|unregister --hostname --type xx
def main():
    parser = argparse.ArgumentParser(prog='Open source softare bundle GitLab CI tools')
    parser.add_argument('--config', help='config file path.')
    parser.add_argument('--db', default=None, help='Gitlab register record file.')

    subs = parser.add_subparsers(dest='cmd')
    subcmd = subs.add_parser('register', help='Register gitlab runner')
    subcmd.add_argument('--type', action="append")
    subcmd.add_argument('--hostname')
    subcmd.add_argument('--platform', default=PLATFORM)

    subcmd = subs.add_parser('unregister', help='Register gitlab runner')
    subcmd.add_argument('--hostname')
    
    subcmd = subs.add_parser('generate', help='Generate gitlab runner config')
    subcmd.add_argument('--type', action="append")
    subcmd.add_argument('--hostname')
    subcmd.add_argument('--platform', default=PLATFORM)
    subcmd.add_argument('--home', default='/home/edgetoolkit')
    subcmd.add_argument('--out', default='./tmp/gitlab-runner')

    args = parser.parse_args()
    manager = GitlabRunnerManager(args.config, args.db)
    if args.cmd == 'register':
        result = manager.register(args.hostname, args.type, args.platform)
    elif args.cmd == 'unregister':
        result = manager.unregister(args.hostname)
    elif args.cmd == 'generate':
        result = manager.generate(args.hostname, args.type, args.platform, args.home, args.out)
    

if __name__ == '__main__':
    main()