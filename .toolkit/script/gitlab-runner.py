import argparse
import yaml
import os
import sys
import gitlab
import shutil

from conans.tools import rmdir
from collections import namedtuple, OrderedDict
from conans.tools import ConanOutput, mkdir
from conans.client.conan_api import ConanAPIV1 as ConanAPI

from utils import jinja_render
_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOTDIR = os.path.normpath(f"{_DIR}/../..")

class GitlabRunnerDB(object):

    def __init__(self, path):
        self.path = os.path.abspath(path)
        self._data = None

    @property
    def data(self):
        if self._data is None:
            try:
                with open(self.path) as f:
                    self._data = yaml.safe_load(f) or {}
            except:
                mkdir(os.path.dirname(self.path))
                self._data = {}
        return self._data

    def _flush(self):
        with open(self.path, 'w') as f:
            yaml.safe_dump(self._data, f)

    def add(self, id, token, name):
        self.data[id] = {'token': token, 'name': name}
        self._flush()


    def delete(self, id):
        if id and id in self.data:
            del self.data[id]
        self._flush()

    def find(self, name):
        for id, value in self.data.items():
            if name == value['name']:
                return id
        return None

    def get(self, id):
        return self.data.get(id)


class GitlabRunner(object):
    GitLabID = None # if not None, means default in ~/.python-gitlab.cfg

    def __init__(self, config, db, out=None):
        self.out = out or ConanOutput(sys.stdout)
        self._config_file = config
        if not os.path.exists(self._config_file):
            self.out.error("config file not exists")
            raise FileNotFoundError(self._config_file)

        with open(self._config_file) as f:
            self.config = yaml.safe_load(f) or {}

        self._machine = None
        self._bundle = None
        filename = db or 'register-db.yml'
        self.db = GitlabRunnerDB(filename)

    @property
    def machine(self):
        if self._machine is None:
            Machine = namedtuple('Machine', ['name', 'host', 'HOME', 'runner', 'tag'])
            tags = self.config.get('tags') or {}
            machines = self.config.get('machine') or {}
            print('>>>>', machines)
            self._machine = {}
            for name, m in machines.items():
                host = m['host']
                HOME = m.get('HOME') or None
                for runner in m['runner'] or []:
                    tag = tags[host][runner]
                    if name not in self._machine:
                        self._machine[name] = []
                    self._machine[name].append(Machine(name, host, HOME, runner, tag))
        return self._machine

    @property
    def bundle(self):
        if self._bundle is None:
            prj_name = self.config.get('name') or ''
            self._bundle = OrderedDict()
            Bundle = namedtuple('Bundle', ['name', 'remote', 'workbench'])
            for bundle in self.config.get('bundle') or []:
                name = bundle['name']
                self._bundle[name] = Bundle(name, bundle.get('remote'), f"{prj_name}.{name}")
        return self._bundle

    @property
    def gitlab(self):
        config_file = os.path.expanduser('~/.python-gitlab.cfg')
        return gitlab.Gitlab.from_config(self.GitLabID, [config_file])

    def parse_args_machine(self, machine):
        if '*' in machine:
            assert len(machine) == 1
            return list(self.machine)
        else:
            print("machine:", machine)
            print("machine:", list(self.machine))
            diff = set(machine) - set(list(self.machine))
            if diff:
               raise LookupError('Invalide machine {}'.format(",".join(diff)))
        #return list(filter(lambda x: x.name in machine, self.machine.values()))
        return machine

    
    def register(self, machines, url=None, token=None):
        url = url or self.config.get('url')
        token = token or self.config.get('token')
        gl = gitlab.Gitlab(url)
        for name in machines:
            for config in self.machine[name]:
                for _, bundle in self.bundle.items():
                    Id = f"{config.name}/{bundle.workbench}/{config.runner}"
                    runner = self._find_runner(Id)
                    tags = config.tag + [f"{bundle.name}@OSS"]
                    if runner:
                        self.out.warn(f"{Id} already registerd.\n{runner}")
                        r = self.gitlab.runners.get(runner.id)
                        r.tag_list = tags
                        r.save()
                        continue
                    runner = gl.runners.create({'token': token,
                                      'description': f"[{Id}]",
                                      'info': {'name': f"{Id}"},
                                      'tag_list': tags
                                      })
                    self.db.add(runner.id, runner.token, Id)
                    self.out.info(f"{Id} registerd. id={runner.id} token={runner.token}")

    def _find_runner(self, name):
        runners = self.gitlab.runners.list()
        for runner in runners:
            if runner.name == name:
                return runner
        return None


    def delete(self, machines, force=False):
        runners = self.gitlab.runners.list()
        for runner in runners:
            for name in machines:
                for config in self.machine[name]:
                    for _, bundle in self.bundle.items():
                        if runner.name == f"{name}/{bundle.workbench}/{config.runner}":
                            runner.delete()
                            self.db.delete(runner.id)
                            self.out.info(f"{runner.id} - {runner.name} deleted.")

    def ls(self, machines=None):
        machines = machines or self._parse_args_machine()
        runners = self.gitlab.runners.list()

        for runner in runners:
            for name in machines:
                for config in self.machine[name]:
                    for bundle in self.bundle:
                        if runner.name == f"{name}/{bundle.workbench}/{config.runner}":
                            print(runner)

    def gen(self, machines, out_dir, url=None):
        machines = machines or self._parse_args_machine()
        runners = self.gitlab.runners.list()
        
        for name in machines:
            content = ""
            for config in self.machine[name]:
                for _, bundle in self.bundle.items():
                    id = self.db.find(f"{config.name}/{bundle.workbench}/{config.runner}")
                    if id:
                        content += self._gen_workbench(id, bundle, config, out_dir) + "\n"
            path = os.path.join(out_dir, name)
            mkdir(path)            
            with open(os.path.join(path, 'config.toml'), 'w') as f:
                f.write(content)

    def _gen_workbench(self, id, bundle, config, rootd, url=None):
        token = self.db.get(id)['token']
        name = self.db.get(id)['name']
        url = url or self.config.get('url')        
        deps = []
        for _, it in self.bundle.items():
            if bundle.name == it.name:
                break
            deps.insert(0, it)
            
        context = {'bundle': bundle, 'deps': deps, 'config': config}
        jinja_render(context, 'workbench/config.yml.j2', f"{rootd}/{config.name}/{bundle.workbench}/{config.runner}/config.yml")
        
        workbench_dir = f"{rootd}/{config.name}/{bundle.workbench}/{config.runner}"
        conan = ConanAPI(f"{workbench_dir}/.conan")
        for remote in conan.remote_list():            
            conan.remote_remove(remote.name)
        conan.remote_add(bundle.name, bundle.remote, verify_ssl=False)

        if config.runner == 'deployer':
            conf = self.config.get('conan') or {}
            username = conf['username']
            password = conf['password']
            conan.authenticate(username, password, bundle.name)
        else:
            for b in self.config.get('bundle') or []:
                if b['name'] == bundle.name:
                    break
                conan.remote_add(b['name'], b['remote'], verify_ssl=False)

        from epm import DATA_DIR    
        # copy settings.yml        
        shutil.copyfile(f"{DATA_DIR}/conan/settings.yml", f"{workbench_dir}/.conan/.settings.yml")

        # copy profiles
        rmdir(f"{workbench_dir}/profiles")    
        shutil.copytree(f"{DATA_DIR}/profiles", f"{workbench_dir}/profiles")

        
        path = f"{rootd}/{config.name}/{bundle.workbench}/script"        
        rmdir(path)
        shutil.copytree(os.path.join(_ROOTDIR, '.toolkit/script/gitlab-runner/script'), path)

        # render gitlab-runner config part
        context.update({'url': url, 'token': token})
        return jinja_render(context, f'gitlab-runner/{config.runner}.toml.j2')


    





class Command(object):
    def __init__(self, args, out):
        self._args = args
        self._out = out
    def register(self):
        gr = GitlabRunner(self._args.config, self._args.db, self._out)
        machines = gr.parse_args_machine(self._args.machine)
        gr.register(machines, self._args.url, self._args.token)

    def delete(self):
        gr = GitlabRunner(self._args.config, self._args.db, self._out)
        machines = gr.parse_args_machine(self._args.machine)
        gr.delete(machines)

    def gen(self):
        gr = GitlabRunner(self._args.config, self._args.db, self._out)
        machines = gr.parse_args_machine(self._args.machine)
        gr.gen(machines, self._args.out)

  
def main():
    _CONFIG_DIR = '.config'
    _CONFIG_FILE = f'{_CONFIG_DIR}/config.yml'
    _REGISTER_DB = f'{_CONFIG_DIR}/register.db.yml'
    out = ConanOutput(sys.stdout, color=True)
    parser = argparse.ArgumentParser(prog='Open source softare bundle GitLab CI tools')
    subs = parser.add_subparsers(dest='cmd')

    def _add_arg(subc):        
        subc.add_argument('--config', default=f'{_CONFIG_FILE}', help='config file path.')
        subc.add_argument('--db', default=f'{_REGISTER_DB}', help='Gitlab register record file.')
        subcmd.add_argument('machine', nargs='+', help='The machine name defined in config file. "*" for all.')
        subcmd.add_argument('--url', default=None, help='Gitlab url, if not set use config file url field.')
    subcmd = subs.add_parser('update', help='Update .gitlab-ci.yml')
    subcmd.add_argument('--package', default=False, action='store_true', help='Update package GitLab CI config only')

    subcmd = subs.add_parser('register', help='Register gitlab runner')
    _add_arg(subcmd)    
    subcmd.add_argument('--token', default=None, help='Gitlab runner auth token, if not set try config file token field.')

    subcmd = subs.add_parser('delete', help='Delete specified machine gitlab runner')
    _add_arg(subcmd)
    subcmd.add_argument('--force', default=False, action='store_true', help='delete if name matched.')

    subcmd = subs.add_parser('gen', help='Generate specifed machine gitlab-runner config files')
    _add_arg(subcmd)
    subcmd.add_argument('--out', default=f'.epm/gitlab-runner', help='Generated files will be stored in ${out}/${machine}. previous exits folder will be removed.')

    args = parser.parse_args()
    cli = Command(args=args, out=out)

    fn = getattr(cli, args.cmd, None)
    if not fn:
        out.error(f"unkown command {args.cmd}.")
        sys.exit(1)
    sys.exit(fn())


if __name__ == '__main__':
    main()