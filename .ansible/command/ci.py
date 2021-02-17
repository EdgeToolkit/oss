import os
import re
import yaml
from collections import namedtuple
from epm.tools.lockfile import FileLock
from epm.utils import Jinja2, abspath, ObjectView
from conans.tools import mkdir, save
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

    def __init__(self, url, access=None, registration=None, db=None):
        token = namedtuple("Token", "access registration")(access, registration)
        self._db_filename = db
        self.conf = namedtuple("Conf", "url token")\
            (url, token)
        self._gitlab = None

    @property
    def gitlab(self):
        if self._gitlab is None:
            self._gitlab = gitlab.Gitlab(self.conf.url, private_token=self.conf.token.access)
        return self._gitlab

    def register(self, n):
        with Dict(self._db_filename) as token:
            for i in range(n):
                runner = self.gitlab.runners.create({'token': self.conf.token.registration})
                token[runner.id] = runner.token
                print(f"{i} -- {runner.id}: {runner.token}")

    def unregister(self, id):
        with Dict(self._db_filename) as token:
            runner = self.gitlab.runners.get(id)
            runner.delete()
            if id in token:
                del token[id]

    def reset(self, hostname='*'):
        """disable all runners"""
        for runner in self.runners(hostname):
            runner.description = f'[free] {id}'
            runner.active = False
            runner.tag_list = None
            runner.save()

    def active(self, hostname=None, state=True):
        for runner in self.runners(hostname):
            runner.active = state
            runner.save()

    @property
    def tokens(self):
        #filename = f"{self.conf.dir}/tokens.yml"
        with Dict(self._db_filename, sync=False) as token:
            return token

    def runners(self, hostname=None):
        runners = []
        for id in self.tokens:
            runner = self.gitlab.runners.get(id)
            m = self.parse_description(runner.description)
            if hostname is None:
                if not m:
                    runners.append(runner)
            else:
                if hostname == '*':
                    runners.append(runner)
                else:
                    if m and m.hostname == hostname:
                        runners.append(runner)
        return runners

    def apply(self, hostname, kind, workbench=None, platform='Linux', arch='adm64'):
        """ apply a configuration for specified host
        """
        if kind == 'trigger':
            kind = 'gitlab-ci.config.generator'
            workbench = None
        assert kind in ['builder', 'tester', 'deployer', 'gitlab-ci.config.generator']

        #filename = f"{self.conf.dir}/tokens.yml"
        #with FileLock(filename, timeout=60):
        # get the first available one
        runner = self.runners()[0]
        tags = [kind]
        if workbench:
            tags += [f"@{workbench}"]

        if kind in ['builder', 'tester']:
            tags += [platform]

        if kind == 'builder':            
            tags += [] if platform == 'Linux' else ['MSVC']

        if kind == 'tester':
            tags += ['docker'] if platform == 'Linux' else []

        description = f"{hostname}/{platform}/{arch}:{kind}"
        if workbench:
            description += f" @{workbench}:{runner.id}"

        self.gitlab.runners.update(runner.id, {'active': False,
            'tag_list': tags, 'description': description})
#
#    def config(self, hostname, builder=0, tester=0, trigger=0, deployer=0,
#               workbench=None, platform='Linux', arch='x86_64'):
#        kinds = {'builder': builder, 'tester': tester, 'trigger': trigger, 'deployer': deployer}
#
#        for kind, n in kinds.items():
#            for i in range(n):
#                self.apply(hostname, kind, workbench, platform)
#
    def make(self, hostname, out_dir):
        self._render_config(hostname, out_dir)

    def _render_config(self, hostname, out_dir, concurrency=1):
        filename = f"{out_dir}/{hostname}/config.toml"
        content = "concurrent = 1\n" \
                  "timeout=1800\n"
        save(filename, content)
        token = self.tokens
        for runner in self.runners(hostname):
            m = self.parse_description(runner.description)
            assert hostname == m.hostname
            context = {'hostname': m.hostname, 'platform': m.platform, 'arch': m.arch,
                       'url': self.conf.url, 'token': token[runner.id], 
                       'description': runner.description, 'id': m.id,
                       'kind': m.kind, 'workbench': m.workbench, 'tags': runner.tag_list}
            kind = context['kind']
            j2 = Jinja2(f"{_DIR}/templates/.gitlab-runner", context)
            content = j2.render(f"{kind}.toml.j2")
            save(filename, content, append=True)

    @staticmethod
    def parse_description(description):
        P = r'(?P<hostname>[\w\.\-]+)/(?P<platform>Windows|Linux)/(?P<arch>(arm|amd|x86|adm)\w*)'
        P += r'\:(?P<kind>builder|tester|deployer|gitlab-ci.config.generator)'
        P += r'(\s+\@workbench\=(?P<workbench>[\w\d\-\.\/]+)\:(?P<id>\d+))?'
        #
        pattern = re.compile(P)
        m = pattern.match(description)
        if m:
            print(m.groups())
            return namedtuple('D', "hostname platform arch kind workbench id")(
                m.group('hostname'), m.group('platform'), m.group('arch'),
                m.group('kind'), m.group('workbench'), m.group('id'))
        return None
