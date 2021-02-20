import os
import re
import gitlab
from collections import namedtuple
from ansible.module_utils.basic import AnsibleModule

class GitlabRunner(object):
    
    FREE_FORMAT = "[{id}] free"

    def __init__(self, db):
        self.db = db
        #print(self.db)
        self._gitlab = None

    @property
    def gitlab(self):
        if self._gitlab is None:
            self._gitlab = gitlab.Gitlab(self.db['url'], self.db['token'])
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
        for rid in self.db.get('runner') or []:
            runner = self.gitlab.runners.get(rid)
            m = self.parse(runner.description)
            if m:
                check = True
                check &= hostname in [None, '*'] or m.hostname == hostname
                if check:
                    runners.append(runner)
        return runners

    def alloc(self):
        for rid in self.db.get('runner') or []:
            runner = self.gitlab.runners.get(rid)
            m = self.parse(runner.description)
            if not m:
                return runner
        return None

    def free(self, hostname):
        runners = []
        for runner in self.find(hostname):
            runner.description = self.FREE_FORMAT.format(id=runner.id)
            runner.active = False
            runner.tag_list = None
            runner.save()
            runners.append(runner.id)

    def active(self, hostname=None, state=True):
        runners = []        
        for runner in self.find(hostname):
            runner.active = state
            runner.save()
            runners.append(runner.id)
        return runners

    def info(self, runner, hostname=None):
        runners = []        
        for runner in self.find(hostname):
            runners.append(self._mkinfo(runner, hostname))
        return runners

    def apply(self, hostname, kind, workbench, platform, arch):
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
        return self._mkinfo(runner, hostname, workbench=workbench, kind=kind, platform=platform, arch=arch)

    def _mkinfo(self, runner, hostname, workbench=None, platform=None, arch=None, kind=None):
        m = self.parse(runner.description)
        hostname = hostname or (m.hostname if m else '?')
        platform = platform or (m.platform if m else '?')
        arch = arch or (m.arch if m else '?')
        kind = kind or (m.kind if m else '?')
        workbench = workbench or (m.workbench if m else '?')
        return {'id': runner.id,        
        'hostname': hostname,
        'token': self.db['runner'][str(runner.id)],
        'platform': platform,
        'arch': arch,
        'tags': runner.tag_list,
        'description': runner.description,
        'kind': kind,
        'workbench': workbench
        }

def main():
    argument_spec = {
        "hostname": {"required": True, "type": "str"},
        "db": {"required": True, "type": "dict"}, 
        "builder": {"default":  None, "type": "int" },
        "tester": {"default": None, "type": "int" },
        "deployer": {"default": None, "type": "int" },
        "trigger": {"default": None, "type": "int" },
        "workbench": {"default": None, "type": "str"},
        "platform": {"default": None, "type": "str"},
        "arch": {"default": None, "type": "str"},
        "command": {
            "required": True, 
            "choices": ['free', 'configure', 'active', 'deactive', 'info'],  
            "type": 'str' 
        },
    }
    module = AnsibleModule(argument_spec=argument_spec)
    db = module.params['db']
    command = module.params['command']
    hostname = module.params['hostname']
    workbench = module.params['workbench']
    platform = module.params['platform']
    arch = module.params['arch']
    try:
        runners = {}
        gl = GitlabRunner(db)        
        if command == 'free':
            runners = gl.free(hostname)
        elif command == 'active':
            runners = gl.active(hostname, True)
        elif command == 'deactive':
            runners = gl.active(hostname, False)
        elif command == 'info':
            runners = gl.info(hostname)
        elif command == 'configure':
            runners = []
            gl.free(hostname)
            for kind in ['builder', 'tester', 'deployer', 'trigger']:
                for i in range(module.params[kind]):
                    runner = gl.apply(hostname, kind, workbench, platform, arch)
                    runners.append(runner)
        else:
            raise Exception('Not implement command <{}>'.format(command))
    except Exception as e:
        module.fail_json(changed=True, msg=str(e))
    else:
        module.exit_json(changed=True, runners=runners)
    

if __name__ == '__main__':
    main()
