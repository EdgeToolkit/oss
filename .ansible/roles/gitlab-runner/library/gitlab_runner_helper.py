import os
import json
import gitlab
from ansible.module_utils.basic import *





class GitlabRunner(object):
    FREE_FORMAT = "[{id}] free"

    def __init__(self, db):
        self.db = db
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
        for rid in self.db.runner:
            runner = self.gitlab.runners.get(rid)
            m = self.parse(runner.description)
            if m:
                check = True
                check &= hostname in [None, '*'] or m.hostname == hostname
                if check:
                    runners.append(runner)
        return runners

    def alloc(self):
        for rid in self.db.token:
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

    def apply(self, hostname, kind, workbench=None, platform, arch):
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
        return {'id': runner.id,
        'token': self.db.runner[runner.id],
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

#        "builder": {"default": 0, "type": "int" },
#        "tester": {"default": 0, "type": "int" },
#        "deployer": {"default": 0, "type": "int" },
#        "trigger": {"default": 0, "type": "int" },
#        "workbench": {"default": 'x', "type": "str"},
#        "platform": {"default": os.getenv('ansible_system', 'y'), "type": "str"},
#        "arch": {"default": os.getenv('ansible_architecture', 'z'), "type": "str"},
        "command": {
            "default": "configure", 
            "choices": ['free', 'configure'],  
            "type": 'str' 
        },
    }
    module = AnsibleModule(argument_spec=argument_spec)
    #db = module.params['db']
    #command = module.params['command']
    #hostname = module.params['hostname']
    #workbench = module.params['workbench']
    #platform = module.params['platform']
    #arch = module.params['arch']
    try:
        runners = []
        #gl = GitlabRunner(db)        
        #if command == 'free':
        #    runners = gl.free(hostname)
        #else:
        #    runners = [] #configure(module.params)
        #    gl.free(hostname)
        #    for kind in ['builder', 'tester', 'deployer', 'trigger']:
        #        for i in range(module.params[kind]):
        #            print(kind)
        #            #print(workbench, platform, arch, '<-')
        #            #gl.apply(hostname, kind, workbench=None, platform, arch)
    except Exception as e:
        module.fail_json(changed=True, msg=str(e))
    else:
        module.exit_json(changed=True, runners=runners)

if __name__ == '__main__':
    main()
