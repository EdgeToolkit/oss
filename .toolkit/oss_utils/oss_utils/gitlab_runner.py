#!/usr/bin/env python3
import os
import yaml
import fnmatch
import gitlab
import platform
import argparse
import shutil
import subprocess

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


class Generater(object):

    def __init__(self, config, hostname, type,  home, platform=None, out_dir=None):
        self._config = config
        self._hostname = hostname
        self._type = [type] if isinstance(type, str) else type
        self._platform = platform or PLATFORM
        self._home = home
        self._out_dir = abspath(out_dir or f"./tmp/gitlab-runner/{hostname}")
        self._workbench = self._config['workbench']
        self.log = {}

    def run(self, gitlab, db):
        if os.path.exists(self._out_dir):
            shutil.rmtree(self._out_dir)
        os.makedirs(self._out_dir)
        self._runner_config(gitlab, db)
        self._gen_workbench()
        #tar zxvf FileName.tar.gz
        subprocess.run(['tar', 'zcvf', f"{self._out_dir}/workbench.tar.gz", "workbench"], cwd=self._out_dir)



    def _runner_config(self, gitlab, db):
        content =  ""
        self.log['config.toml'] ={}
        for workbench in self._workbench:
            for type in self._type:                
                cli = GitlabRunner(self._hostname, type, workbench=workbench, gitlab=gitlab, db=db)
                runner = cli.runner
                if not runner:
                    raise Exception(f'can not get {cli.name} runner')
                id = runner.id
                item = db.get(id)
                if not item:
                    raise Exception(f'{id} not found in hash table')
                context = {'platform': self._platform, 'token': item['token'], 
                           'id': id, 'url': self._config['gitlab']['url'],
                           'HOME': self._home, 'workbench': workbench, 'hostname': self._hostname
                           }
                content += self._render(f"{type}.toml.j2", context)
                self.log['config.toml'][f"{workbench}/{type}"] = {'context': context, 'offset': len(content)}

        with open(f"{self._out_dir}/config.toml", 'w') as f:
            f.write(content)
        self.log['config.toml'][f"{self._out_dir}/config.toml"] = len(content)

    def _gen_workbench(self):
        template_dir = os.path.join(DATA_DIR, 'gitlab-runner', 'workbench')

        for workbench in self._workbench:
            for type in self._type:
                dst_dir = f"{self._out_dir}/workbench/{workbench}/{type}"
                for i in ['', '.conan/hooks']:
                    if not os.path.exists(f"{dst_dir}/{i}"):
                        os.makedirs(f"{dst_dir}/{i}")
                for i in ['script', 'profiles']:
                    shutil.copytree(f"{template_dir}/{i}", f"{dst_dir}/{i}")

                shutil.copy(f"{template_dir}/conan/hooks/{type}.py", f'{dst_dir}/.conan/hooks/{type}.py')
                self._workbench_remote(workbench, type)
                self._workbench_config(workbench, type)

    def _workbench_remote(self, workbench, type):
        dst_dir = f"{self._out_dir}/workbench/{workbench}/{type}"
        os.environ['CONAN_USER_HOME'] = os.path.abspath(dst_dir)
        subprocess.run(['conan', 'remote', 'clean'], check=True)
        if type == 'deployer':
            os.environ['CONAN_REVISIONS_ENABLED'] = '1'
            for remote in self._workbench[workbench]['conan'] or []:
                if remote['name'] != workbench:
                    continue
                # conan remote add remote url False
                subprocess.run(['conan', 'remote', 'add', remote['name'], remote['url'], 'False'], check=True)

                # conan user -p password -r remote remote username
                subprocess.run(['conan', 'user', '-r', remote['name'], '-p', remote['password'], remote['username']],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,           check=True)
                break
        else:
            for remote in self._config['workbench'][workbench]['conan'] or []:
                # conan remote add remote url False
                subprocess.run(['conan', 'remote', 'add', remote['name'], remote['url'], 'False'], check=True)

    def _workbench_config(self, workbench, type):
        path = f"{self._out_dir}/workbench/{workbench}/{type}"
        remote = self._workbench[workbench]['conan'] or []
        enviroment = self._config.get('environment') or {}
        context = {'workbench': workbench, 'remote': remote, 'enviroment': enviroment}
        self._render("workbench/config.yml.j2", context, f"{path}/config.yml")


    @staticmethod
    def _template(filename):
        path = os.path.join(DATA_DIR, 'gitlab-runner')
        env = Environment(loader=FileSystemLoader(path))
        #env.trim_blocks = True
        #template_file = os.path.basename(filename)
        return env.get_template(filename)

    @staticmethod
    def _render(template_file, context, outfile=None):
        template = Generater._template(template_file)
        txt = template.render(context)
        if outfile:
            folder = os.path.dirname(outfile)
            if not os.path.exists(folder):
                os.makedirs(folder)
            with open(outfile, 'w') as f:
                f.write(txt)
        return txt

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
        gen = Generater(self.config, hostname=hostname, type=type, 
                        home=home, platform=platform, out_dir=out_dir)
        gen.run(self.gitlab, self.db)
        return gen.log


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