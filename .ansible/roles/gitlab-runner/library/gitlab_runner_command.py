import os
import re
import time
import errno
import gitlab
from collections import namedtuple
from ansible.module_utils.basic import AnsibleModule

class FileLockException(Exception):
    pass

class FileLock(object):
    """ A file locking mechanism that has context-manager support so
        you can use it in a with statement. This should be relatively cross
        compatible as it doesn't rely on msvcrt or fcntl for the locking.
    """

    def __init__(self, file_name, timeout=10, delay=.05):
        """ Prepare the file locker. Specify the file to lock and optionally
            the maximum timeout and the delay between each attempt to lock.
        """
        self.is_locked = False
        self.lockfile = os.path.join(os.getcwd(), "%s.lock" % file_name)
        self.file_name = file_name
        self.timeout = timeout
        self.delay = delay

    def acquire(self):
        """ Acquire the lock, if possible. If the lock is in use, it check again
            every `wait` seconds. It does this until it either gets the lock or
            exceeds `timeout` number of seconds, in which case it throws
            an exception.
        """
        start_time = time.time()
        while True:
            try:
                self.fd = os.open(self.lockfile, os.O_CREAT | os.O_EXCL | os.O_RDWR)
                break
            except OSError as e:
                if e.errno != errno.EEXIST:
                    raise
                if (time.time() - start_time) >= self.timeout:
                    raise FileLockException("Timeout occured.")
                time.sleep(self.delay)
        self.is_locked = True

    def release(self):
        """ Get rid of the lock by deleting the lockfile.
            When working in a `with` statement, this gets automatically
            called at the end.
        """
        if self.is_locked:
            os.close(self.fd)
            os.unlink(self.lockfile)
            self.is_locked = False

    def __enter__(self):
        """ Activated when used in the with statement.
            Should automatically acquire a lock to be used in the with block.
        """
        if not self.is_locked:
            self.acquire()
        return self

    def __exit__(self, type, value, traceback):
        """ Activated at the end of the with statement.
            It automatically releases the lock if it isn't locked.
        """
        if self.is_locked:
            self.release()

    def __del__(self):
        """ Make sure that the FileLock instance doesn't leave a lockfile
            lying around.
        """
        self.release()

def lock(f):
    def wrapper(this, *args, **kwargs):
        if this._lockfile:
            with FileLock(this._lockfile, timeout=10*60, delay=1):
                return f(this, *args, **kwargs)
        else:
            return f(this, *args, **kwargs)
    return wrapper

class GitlabRunner(object):
    
    FREE_FORMAT = "[{id}] free"

    def __init__(self, db, lockfile=None):
        self.db = db
        self._gitlab = None
        self._logs = []
        self._lockfile = lockfile

    @property
    def gitlab(self):
        if self._gitlab is None:
            self._gitlab = gitlab.Gitlab(self.db['url'], self.db['token'])
        return self._gitlab

    def parse(self, description):
        P = r'(?P<hostname>[\w\.\-]+)/(?P<platform>Windows|Linux)/(?P<arch>(arm|amd|x86)\w*)'
        P += r'\:(?P<kind>builder|runner|deployer|gitlab-ci.config.generator)'
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
                if hostname in [None, '*'] or m.hostname == hostname:
                    runners.append(runner)
        return runners


    def alloc(self):
        for rid in self.db.get('runner') or []:
            runner = self.gitlab.runners.get(rid)
            m = self.parse(runner.description)
            if not m:
                return runner
        return None

    @lock
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

    def info(self, hostname=None):
        runners = []        
        for runner in self.find(hostname):
            runners.append(self._mkinfo(runner, hostname))
        return runners

    @lock
    def apply(self, hostname, kind, workbench, platform, arch):
        if kind == 'trigger':
            kind = 'gitlab-ci.config.generator'
            workbench = None

        runner = self.alloc()

        runner.tag_list = [kind]
        if kind in ['builder', 'runner']:
            runner.tag_list += [platform]

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
        folder = f"{workbench}/{kind}/{runner.id}"
        return {'id': runner.id,        
        'hostname': hostname,
        'token': self.db['runner'][str(runner.id)],
        'platform': platform,
        'arch': arch,
        'tags': runner.tag_list,
        'description': runner.description,
        'kind': kind,
        'workbench': folder,
        }

def main():
    argument_spec = {
        "hostname": {"required": True, "type": "str"},
        "db": {"required": True, "type": "dict"}, 
        "builder": {"default":  None, "type": "int" },
        "runner": {"default": None, "type": "int" },
        "deployer": {"default": None, "type": "int" },
        "trigger": {"default": None, "type": "int" },
        "workbench": {"default": None, "type": "str"},
        "platform": {"default": None, "type": "str"},
        "arch": {"default": None, "type": "str"},
        "lock": {"default": None, "type": "str"},
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
    lock = module.params['lock']
    try:
        runners = {}
        gl = GitlabRunner(db, lock)        
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
            for kind in ['builder', 'runner', 'deployer', 'trigger']:
                for i in range(module.params[kind]):
                    runner = gl.apply(hostname, kind, workbench, platform, arch)
                    runners.append(runner)
        else:
            raise Exception('Not implement command <{}>'.format(command))
    except Exception as e:
        module.fail_json(changed=True, msg=str(e))
    else:
        module.exit_json(changed=True, runners=runners, logs=gl._logs)
    

if __name__ == '__main__':
    main()
