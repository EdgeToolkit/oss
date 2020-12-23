#!/usr/bin/env python3
import os
import sys
import yaml

import os
import gitlab
from collections import namedtuple

#from conans.tools import ConanOutput
import gitlab

class ObjectView(object):
    """Object view of a dict, updating the passed in dict when values are set
    or deleted. "ObjectView" the contents of a dict...: """

    def __init__(self, d):
        # since __setattr__ is overridden, self.__dict = d doesn't work
        object.__setattr__(self, '_ObjectView__dict', d)

    # Dictionary-like access / updates
    def __getitem__(self, name):
        value = self.__dict[name]
        if isinstance(value, dict):  # recursively view sub-dicts as objects
            value = ObjectView(value)
        elif isinstance(value, (list, tuple, set)):
            value = []
            for i in self.__dict[name]:
                if isinstance(i, dict):
                    value.append(ObjectView(i))
                else:
                    value.append(i)

        return value

    def __iter__(self):
        return iter(self._ObjectView__dict)

    def __setitem__(self, name, value):
        self.__dict[name] = value

    def __delitem__(self, name):
        del self.__dict[name]

    # Object-like access / updates
    def __getattr__(self, name):
        return self[name] if name in self else None

    def __setattr__(self, name, value):
        self[name] = value

    def __delattr__(self, name):
        del self[name]

    def __repr__(self):
        return "%s(%r)" % (type(self).__name__, self.__dict)

    def __str__(self):
        return str(self.__dict)


class GitlabRunnerDB(object):

    def __init__(self, path):
        self._path = os.path.expanduser(path) if path else None
        self._runner = {}
        if os.path.exists(self._path):
            with open(self._path) as f:
                self._runner = yaml.safe_load(f) or {}

    def delete(self, id):
        if id in self._runner:
            del self._runner[token]
            self._flush()

    def add(self, id, token=None, name=None):
        self._runner[id] = {'token': token, 'name': hash }
        self._flush()
        
    def token(self, id):
        return self._runner.get(id, None) or None

    def _flush(self):
        if not self._path:
            return
        folder = os.path.dirname(self._path)
        if not os.path.exists(folder):
            os.makedirs(folder)
        with open(self._path, 'w') as f:
            yaml.safe_dump(self._runner, f, default_flow_style=False)

def find_by_name(data, name):
    for l in data:
        if name == l.get('name'):
            return l
    return None


def load_config(path):
    path = os.path.expanduser(path)
    with open(path) as f:
        data = yaml.safe_load(f)

    workbench = data.pop('workbench', None) or {}
    conan = data.pop('conan', None) or {}    
    username = conan.get('username', None)
    password = conan.get('password', None)
    remote = conan.pop('remote', None) or []
    for i in range(len(remote)):
        remote[i] = dict({'username':username, 'password':password}, **remote[i])
    conan = {'username': username, 'passworkd': password, 'remote': remote}

    data['gitlab'] = dict({'group':None}, **data['gitlab'])
    
    for i in range(len(workbench)):
        result = []
        for name in workbench[i].get('remote',[]) or []:
            r = find_by_name(remote, name)
            result.append(r)
        workbench[i]['remote'] = result

    data['workbench'] = workbench
    data['conan'] = conan
    config = ObjectView(data)
    return config
        
def gitlab_runner_hash(hostname, type, workbench, tag=[]):
    tag = list(tag)
    tag.sort()
    return f"{hostname}/{type}/{workbench}/" + "[{}]".format(",".join(tag))



class _GitlabRunner(object):

    def __init__(self, hostname, type, workbench, device_hostname=None):
        self.hostname = hostname
        self.type = type
        self.workbench = workbench
        self.device_hostname = device_hostname
        
    @property
    def name(self):
        name = f"{self.hostname}/{self.type}/{self.workbench}" 
        return f"{name}/{self.device_hostname}" if self.device_hostname else name


class GitlabRunner(object):
    # Type
    BUILDER = 'builder'
    RUNNER = 'runner'
    DEPLOYER = 'deployer'

    def __init__(self, config, db=None):
        """
        config_file
        rec_file: gitlab runner token , id record files
        """
        self.config = config
        self.db = db
        self._gitlab = None

    @property
    def gitlab(self):
        if self._gitlab is None:
            url = self.config.gitlab.url
            token = self.config.gitlab.private_token
            self._gitlab = gitlab.Gitlab(url, private_token=token)
        return self._gitlab

    def register(self, hostname, type, workbench, tag):
        hash = gitlab_runner_hash(hostname, type, workbench, tag)
        if self.get(hostname, type, workbench, tag) is None:
            description = f"{hostname}/{type}/{workbench}"
            token = self.config.gitlab.register_token
            runner = self.gitlab.runners.create({'token': token,
                                      'description': description,
                                      'tag_list': tag,
                                      'info': {'name': hash}
                                      })
            self.db.add(runner.id, token=runner.token, hash=hash)

    def register_host(self, hostname, platform, type):        
        common_tags = self.config.tag[platform][type]
        print(common_tags,'###########################', platform, type)
        print(self.config.tag[platform])
        for workbench in self.config.workbench:
            tags = [f"{workbench.name}@workbench"]
            self.register(hostname, type, workbench.name, tags+common_tags)

    def remove_host(self, hostname):
        for runner in self.gitlab.runners.list():
            if runner.name and runner.name.startswith(hostname):
                runner.delete()


    def delete(self):
        runner = self.get()
        if runner:
            runner.delete()

    def get(self, hostname, type, workbench, tag):
        hash = gitlab_runner_hash(hostname, type, workbench, tag)
        for runner in self.gitlab.runners.list():
            if hash ==  runner.name:
                return runner
        return None

    def generate(self, filename, hostname, type, platform):
        context = {'hostname': hostname, 'platform': platform}
        for workbench in self.db.workbench:
            runner = self.get(hostname, type, workbench)


    def update(self, tags):
        pass

import argparse

def main():
    parser = argparse.ArgumentParser(prog='Open source softare bundle GitLab CI tools')
    subs = parser.add_subparsers(dest='cmd')
    def _add_arg(subc):        
        subc.add_argument('--config', help='config file path.')
        subc.add_argument('--db', default=None, help='Gitlab register record file.')

    subcmd = subs.add_parser('register', help='Register gitlab runner')
    _add_arg(subcmd)    
    subcmd.add_argument('--type', action="append")
    subcmd.add_argument('--hostname')
    subcmd.add_argument('--platform')

    subcmd = subs.add_parser('delete', help='remove gitlab runner')
    _add_arg(subcmd)
    subcmd.add_argument('--hostname')
    args = parser.parse_args()
    config = load_config(args.config)
    db = GitlabRunnerDB(args.db) if args.db else None
    gitlab_runner = GitlabRunner(config, db)
    
    if args.cmd == 'register':
        print('platform==============', args.platform)
        for type in args.type:
            gitlab_runner.register_host(args.hostname, args.platform, type)
    if args.cmd == 'delete':
        gitlab_runner.remove_host(args.hostname)

if __name__ == '__main__':
    main()