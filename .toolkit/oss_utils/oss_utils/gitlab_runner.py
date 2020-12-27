#!/bin/bash env python3
import os
import yaml
import fnmatch
import gitlab
import platform
import argparse
import shutil

from jinja2 import Environment, FileSystemLoader

PLATFORM = platform.system()


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

class GitlabRunnerDB(object):

    def __init__(self, path):
        self._path = os.path.abspath(os.path.expanduser(path) if path else None)
        self._item = None

    @property
    def item(self):
        if self._item is None:
            self._item = {}
            if os.path.exists(self._path):
                with open(self._path) as f:
                    self._item = yaml.safe_load(f) or {}
        return self._item

    def delete(self, id):
        if id in self.item:
            del self.item[id]
            self._flush()

    def add(self, id, token, comment=None):
        self.item[id] = {'token': token, 'comment': comment }
        self._flush()

    def remove_by_id(self, id):
        if id in self.item:
            token = self.item[id]['token']
            del self.item[id]
            return token
        return None

    def remove_by_token(self, token):
        for id, runner in self.item.items():
            if token == runner['token']:
                del self.item[id]
                return id
        return None

    def get_token(self, id):
        item = self.item.get(id, None)
        return item['token'] if item else None

    def get_id(self, token):
        for id, runner in self.item.items():
            if runner['token'] == token:
                return id
        return None

    def _flush(self):
        if not self._path:
            return
        folder = os.path.dirname(self._path)
        if not os.path.exists(folder):
            os.makedirs(folder)
        with open(self._path, 'w') as f:
            yaml.safe_dump(self.item, f, default_flow_style=False)

    @property
    def filename(self):
        return self._path


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
            self._db.add(runner.id, token=runner.token, comment=self.name)            
        return runner

    def unregister(self):
        result = []
        runner = self.runner
        if runner:
            runner.delete()
            self._db.remove_by_id(runner.id)
            result.append(runner)
        return result
    
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
            self.db = GitlabRunnerDB(self.db)
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
                tags = self.config['tag'][platform][runner_type]

                cli = GitlabRunner(hostname, type, workbench=workbench,gitlab=self.gitlab, db=self.db)
                runner = cli.register(register_token, tags)
                result.append(runner)
        return result


    def unregister(self, hostname):
        result = []
        for runner in self.gitlab.runners.list():
            if runner.name and isinstance(runner.name, str):
                r = GitlabRunner.load(runner.name)
                if r.hostname != hostname:
                    continue
                # TODO: more confition
                
                runner.delete() 
                if self.db:
                    self.db.remove_by_id(runner.id)
                result.append(runner)
        return result

    def mkconfig(self, hostname, type, platform, home):
        types = [type] if isinstance(type, str) else type
        register_token = self.config['gitlab']['register_token']
        platform = platform or PLATFORM
        result = []
        content =  ""
        for workbench in self.config['workbench']:
            for rtype in types:                
                cli = GitlabRunner(hostname, rtype, workbench=workbench, gitlab=self.gitlab, db=self.db)
                id = cli.runner.id
                token = self.db.get_token(id)
                url = self.config['gitlab']['url']
                template = self._template(f"{rtype}.toml.j2")
                content += template.render(platform=platform, token=token, id=id, url=url, HOME=home, workbench=workbench)
        rootd = f".gitlab-runner-config/{hostname}"
        rootd = os.path.expanduser(f"/tmp/gitlab-runner-config/{hostname}")

        if os.path.exists(rootd):
            shutil.rmtree(rootd)
        os.makedirs(rootd)
        with open(os.path.join(rootd, 'config.toml'), 'w') as f:
            f.write(content)

        TWD = os.path.join(os.path.dirname(__file__), 'data', 'gitlab-runner', 'workbench')

        for workbench in self.config['workbench']:
            for rtype in types:
                folder = f"{rootd}/{workbench}/{rtype}"
                os.makedirs(os.path.join(folder))
                shutil.copytree(os.path.join(TWD, 'conan'), os.path.join(folder, '.conan'))
                shutil.copytree(os.path.join(TWD, 'script'), os.path.join(folder, 'script'))                
                # generate conan files
                import subprocess
                os.environ['CONAN_USER_HOME'] = os.path.abspath(folder)
                subprocess.run(['conan', 'remote', 'clean'], check=True)
                for remote in self.config['workbench'][workbench]['conan'] or []:
                    # conan remote add remote url False
                    subprocess.run(['conan', 'remote', 'add', remote['name'], remote['url'], 'False'], check=True)
                if rtype == 'deployer':
                    # conan user -p password -r remote remote
                    pass
        

    @staticmethod
    def _template(filename):
        DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
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
    
    subcmd = subs.add_parser('mkconfig', help='Generate gitlab runner config')
    subcmd.add_argument('--type', action="append")
    subcmd.add_argument('--hostname')
    subcmd.add_argument('--platform', default=PLATFORM)
    subcmd.add_argument('--home', default='/home/edgetoolkit')

    args = parser.parse_args()
    manager = GitlabRunnerManager(args.config, args.db)
    if args.cmd == 'register':
        result = manager.register(args.hostname, args.type, args.platform)
    elif args.cmd == 'unregister':
        result = manager.unregister(args.hostname)
    elif args.cmd == 'mkconfig':
        result = manager.mkconfig(args.hostname, args.type, args.platform, args.home)
    

if __name__ == '__main__':
    main()