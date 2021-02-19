import os
import re
import yaml
import argparse
from collections import namedtuple
from epm.tools.lockfile import FileLock
from conans.tools import mkdir
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


class GitlabRunnerRegister(object):

    def __init__(self, url, db=None):
        self._url = url
        self._filename = db

    def register(self, registration_token):
        if self._registration_token:
            gl = gitlab.Gitlab(self._url)
            runner = gl.runners.create({'token': registration_token})
            if self._filename:
                with Dict(self._filename) as db:
                    db[runner.id] = runner.token
            return runner
        return None

    def unregister(self, id, private_token):
        def _del(x):
            gl = gitlab.Gitlab(self._url, private_token=private_token)
            runner = gl.runners.get(x)
            runner.delete()

        if self._filename:
            with Dict(self._filename) as db:
                if id not in db:
                    raise FileNotFoundError(f'unregister runner <{id}> not in db.')
                _del(id)
                del db[id]
        else:
            _del(id)

    def clear(self, private_token):
        with Dict(self._filename, sync=False) as tokens:
            pass
        for id in tokens:
            self.unregister(id, private_token)


class GitlabRunner(object):
    FREE_FORMAT = "[{id}] free"

    def __init__(self, url, private_token, db):
        self._private_token = private_token
        self._url = url
        self._db = None
        self._filename = db
        self._gitlab = None

    @property
    def db(self):
        if self._db is None and self._filename:
            with Dict(self._filename, sync=False) as token:
                self._db = namedtuple("DB", "token")(token)
        return self._db

    @property
    def gitlab(self):
        if self._gitlab is None:
            self._gitlab = gitlab.Gitlab(self._url, private_token=self._private_token)
        return self._gitlab

    def parse(self, description):
        P = r'(?P<hostname>[\w\.\-]+)/(?P<platform>Windows|Linux)/(?P<arch>(arm|amd|x86|adm)\w*)'
        P += r'\:(?P<kind>builder|tester|deployer|gitlab-ci.config.generator)'
        P += r'(\s+\@(?P<workbench>[\w\d\-\.\/]+)\:(?P<id>\d+))?'
        #
        pattern = re.compile(P)
        m = pattern.match(description)
        if m:
            return namedtuple('D', "hostname platform arch kind workbench id")(
                m.group('hostname'), m.group('platform'), m.group('arch'),
                m.group('kind'), m.group('workbench'), m.group('id'))
        return None

    def find(self, hostname=None):
        runners = []
        for rid in self.db.token:
            runner = self.gitlab.runners.get(rid)
            m = self.parse(runner.description)
            if m:
                check = True
                check &= hostname in [None, '*'] or m.hostname == hostname
                if check:
                    runners.append(runner)
        return runners

    def match(self, hostname=None):
        hostname = re.compile(hostname) if isinstance(hostname, str) else hostname
        runners = []
        for rid in self.db.token:
            runner = self.gitlab.runners.get(rid)
            m = self.parse(runner.description)
            if m:
                check = True
                check &= hostname is None or re.match(hostname, m.hostname)
                if check:
                    runners.append(runner)
        return runners

    def info(self, hostname):
        info = []
        for runner in self.find(hostname):
            m = self.parse(runner.description)
            element = {'id': runner.id, 'tags': runner.tag_list,
            'description': runner.description, 
            'kind': m.kind, 'workbench': m.workbench}
            info.append(element)
        return info

    def alloc(self):
        for rid in self.db.token:
            runner = self.gitlab.runners.get(rid)
            m = self.parse(runner.description)
            if not m:
                return runner
        return None

    def reset(self):
        for rid in self.db.token:
            runner = self.gitlab.runners.get(rid)
            runner.description = self.FREE_FORMAT.format(id=runner.id)
            runner.active = False
            runner.tag_list = None
            runner.save()

    def free(self, hostname):
        runners = self.match(hostname) if hasattr(hostname, 'search') else self.find(hostname)
        for runner in runners:
            runner.description = self.FREE_FORMAT.format(id=runner.id)
            runner.active = False
            runner.tag_list = None
            runner.save()

    def active(self, hostname=None, state=True):
        runners = self.match(hostname) if hasattr(hostname, 'search') else self.find(hostname)
        for runner in runners:
            runner.active = state
            runner.save()

    def apply(self, hostname, kind, workbench=None, platform='Linux', arch='adm64'):
        if kind == 'trigger':
            kind = 'gitlab-ci.config.generator'
            workbench = None
        assert kind in ['builder', 'tester', 'deployer', 'gitlab-ci.config.generator']
        runner = self.alloc()
        assert runner, "No free runners"

        runner.tag_list = [kind]
        if kind in ['builder', 'tester']:
            runner.tag_list += [platform]

        if kind == 'builder' and platform == 'Windows':
            runner.tag_list += ['MSVC']

        if kind == 'tester' and platform == 'Linux':
            runner.tag_list += ['docker']

        runner.description = f"{hostname}/{platform}/{arch}:{kind}"
        if workbench:
            runner.tag_list += [f"@{workbench}"]
            runner.description += f" @{workbench}:{runner.id}"

        runner.active = False
        runner.save()

    def mkconfig(self, hostname, filename, concurrency=1):
        content = "concurrent = 1\n" \
                  "timeout=1800\n"
        save(filename, content)
        runners = self.match(hostname) if hasattr(hostname, 'search') else self.find(hostname)
        for runner in runners:
            desc = self.parse(runner.description)
            assert desc
            context = {'runner': runner, 'metadata': desc, 'url': self._url, 'token': self.db.token[runner.id]}
            j2 = Jinja2(f"{_DIR}/templates/.gitlab-runner", context)
            content = j2.render(f"{desc.kind}.toml.j2")
            save(filename, content, append=True)

    def mkworkbench(self, hostname, out, remote, environment, username=None, password=None):
        runners = self.match(hostname) if hasattr(hostname, 'search') else self.find(hostname)

        for runner in runners:
            m = self.parse(runner.description)
            context = {'runner': runner, 'metadata': m, 'url': self._url, 'token': self.db.token[runner.id],
                       'remote': remote,
                       'environment': environment or [],
                       'workbench': "oss/{}/{}".format(m.kind, runner.id)
                       }
            j2 = Jinja2(f"{_DIR}/templates/workbench/", context)
            path = abspath(f"{out}/{m.kind}/{runner.id}")
            j2.render('config.yml.j2', outfile=f"{path}/config.yml")
            from conans.tools import environment_append
            from subprocess import run
            with environment_append({'CONAN_USER_HOME': path}):
                run('conan remote clean')
                run(f'conan remote add oss {remote} False')
                if m.kind == 'deployer' and username and password:
                    run(f'conan user -p {password} -r {remote} {username}')




class GitlabRunnerCommand(object):

    def __init__(self):
        pass

    def register(self, args):
        register = GitlabRunnerRegister(args.url, args.db)
        register.register(args.token)

    def free(self, args):
        gl = GitlabRunner(args.url, args.token, args.db)
        for hostname in args.hostname:
            gl.free(hostname)

    def reset(self, args):
        gl = GitlabRunner(args.url, args.token, args.db)
        gl.reset()

    def active(self, args):
        gl = GitlabRunner(args.url, args.token, args.db)
        for hostname in args.hostname:
            gl.active(hostname, not args.disable)

    def apply(self, args):
        gl = GitlabRunner(args.url, args.token, args.db)
        for hostname in args.hostname:
            for kind in ['builder', 'tester', 'deployer', 'trigger']:
                n = getattr(args, kind, 0)
                for i in range(n):
                    gl.apply(hostname, kind, args.workbench, args.platform, args.arch)

    def mkconfig(self, args):
        gl = GitlabRunner(args.url, args.token, args.db)
        gl.mkconfig(args.hostname, args.filename)

    def mkworkbench(self, args):
        gl = GitlabRunner(args.url, args.token, args.db)
        environment = {}
        for e in args.environment or []:
            name, value = e.split('=')
            environment[name] = value
        for hostname in args.hostname:
            gl.mkworkbench(hostname, args.out, args.remote, environment)

    def info(self, args):
        import json
        gl = GitlabRunner(args.url, args.token, args.db)
        info = gl.info(args.hostname)
        text = json.dumps(info)
        print(text)

    def _add_argument(self, parser, name, help, url="GitLab url", token="private token to access GitLab",
                     db="GitLab metadata filename", hostname="Hostname that take this action."):
        cmd = parser.add_parser(name, help=help)
        if url:
            cmd.add_argument('--url', required=True, help=url)
        if token:
            cmd.add_argument('--token', required=True, help=token)
        if db:
            cmd.add_argument('--db', required=True, help=db)
        if hostname:
            cmd.add_argument('hostname', type=str, nargs='+', help=hostname)

        fn = getattr(self, name, None)
        if fn:
            cmd.set_defaults(func=fn)
        return cmd

    def main(self, argv):
        parser = argparse.ArgumentParser(prog='Open source software gitlab command tools')
        subs = parser.add_subparsers(dest='sub_command')

        self._add_argument(subs, 'register', help='Register gitlab-runner',
                           token='Gitlab runner registration token', hostname=None)
        self._add_argument(subs, 'reset', help='', hostname=None)
        self._add_argument(subs, 'free', help='')

        cmd = self._add_argument(subs, 'active', help='')
        cmd.add_argument('--disable', default=False, action='store_true', help='')

        cmd = self._add_argument(subs, 'apply', help='')
        cmd.add_argument('--builder', type=int, default=0, help='')
        cmd.add_argument('--tester', type=int, default=0, help='')
        cmd.add_argument('--deployer', type=int, default=0, help='')
        cmd.add_argument('--trigger', type=int, default=0, help='')
        cmd.add_argument('--platform', required=True, help='')
        cmd.add_argument('--arch', default='adm64', help='')
        cmd.add_argument('--workbench', default=None, help='')

        cmd = self._add_argument(subs, 'mkconfig', help='', hostname=None)
        cmd.add_argument('hostname', type=str, help='')
        cmd.add_argument('-f', '--filename', required=True, help='')

        cmd = self._add_argument(subs, 'info', help='', hostname=None)
        cmd.add_argument('hostname', type=str, help='')

        cmd = self._add_argument(subs, 'mkworkbench', help='')
        cmd.add_argument('--out', default="_workbench", type=str, help='')
        cmd.add_argument('--remote', required=True, type=str, help='')
        cmd.add_argument('-e', '--environment', action="append", type=str, help='')

        args = parser.parse_args(argv)
        return args.func(args)


if __name__ == '__main__':
    import sys
    cmd = GitlabRunnerCommand()
    cmd.main(sys.argv[1:])
