import os
import re
import yaml
from collections import namedtuple
from epm.utils import Jinja2, abspath
from conans.tools import mkdir
import gitlab
_DIR = os.path.dirname(abspath(__file__))


class Dict(object):

    def __init__(self, filename, sync=True):
        self._filename = abspath(filename)
        self._sync = sync
        self._data = {}

    def __enter__(self):
        if self._sync:
            mkdir(os.path.dirname(self._filename))
        try:
            with open(self._filename) as f:
                self._data = yaml.safe_load(f) or {}
        except:
            pass
        return self._data

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._sync:
            with open(self._filename, 'w') as f:
                yaml.safe_dump(self._data, f)


class GitlabRunner(object):

    def __init__(self, url, conf_dir, access=None, registration=None):
        token = namedtuple("Token", "access registration")(access, registration)
        self.conf = namedtuple("Conf", "url dir token")\
            (url, conf_dir, token)
        self._gitlab = None

    @property
    def gitlab(self):
        if self._gitlab is None:
            self._gitlab = gitlab.Gitlab(self.conf.url, private_token=self.conf.token.access)
        return self._gitlab

    def register(self, n):
        with Dict(f"{self.conf.dir}/tokens.yml") as token:
            for i in range(n):
                runner = self.gitlab.runners.create({'token': self.conf.token.registration})
                token[runner.id] = runner.token
                print(f"{i} -- {runner.id}: {runner.token}")

    def reset(self):
        """disable all runners"""
        with Dict(f"{self.conf.dir}/tokens.yml", sync=False) as token:
            with Dict(f"{self.conf.dir}/runners.yml") as runners:
                for id in runners:
                    runner = self.gitlab.runners.get(id)
                    runner.description = f'#{id}'
                    runner.active = False
                    runner.tag_list = None
                    runner.save()
                runners.clear()

    def unregister(self, id):
        with Dict(f"{self.conf.dir}/tokens.yml") as token:
            runner = self.gitlab.runners.get(id)
            runner.delete()
            if id in token:
                del token[id]

    def add(self, hostname, kind, workbench=None, platform='Linux'):
        context = {'hostname': hostname, 'workbench': workbench, 'kind': kind, 'platform': platform,
                   }

        with Dict(f"{self.conf.dir}/tokens.yml", sync=False) as token:
            with Dict(f"{self.conf.dir}/runners.yml") as runners:
                available = set(token.keys()).difference(set(runners.keys()))
                id = available.pop()
                tags = [kind]
                if workbench:
                    tags += [f"workbench={workbench}"]

                if kind == 'builder':
                    tags += [platform]
                    tags += [] if platform == 'Linux' else ['MSVC']
                elif kind in ['publisher', 'ci-config-generator']:
                    tags += ['docker']
                description = f"{hostname}/{platform} {kind}"
                if workbench:
                    description += f"@{workbench}"
                value = {'tag_list': tags, 'description': description}
                self.gitlab.runners.update(id, value)
                value.update(context)
                runners[id] = value