import os
import re
import sys
import argparse
from epm.utils import Jinja2, abspath

_DIR = os.path.dirname(abspath(__file__))
from ci import GitlabRunner


def gitlab_runner_register(args):
    gitlab_runner = GitlabRunner(args.url, registration=args.token, db=args.db)
    gitlab_runner.register(args.count)


def gitlab_runner_reset(args):

    gitlab_runner = GitlabRunner(args.url, access=args.token, db=args.db)
    gitlab_runner.reset(args.hostname)


def gitlab_runner_config(args):
    gitlab_runner = GitlabRunner(args.url, access=args.token, db=args.db)
    for kind in ['builder', 'tester', 'deployer', 'trigger']:
        n = getattr(args, kind, 0)
        for i in range(n):
            gitlab_runner.apply(args.hostname, kind, args.workbench, 
            platform=args.platform, arch=args.arch)

def gitlab_runner_active(args):
    gitlab_runner = GitlabRunner(args.url,access=args.token, db=args.db)
    gitlab_runner.active(args.hostname, True)

def gitlab_runner_deactive(args):
    gitlab_runner = GitlabRunner(args.url, access=args.token, db=args.db)
    gitlab_runner.active(args.hostname, False)

def gitlab_runner_make(args):
    gitlab_runner = GitlabRunner(args.url, access=args.token, db=args.db)
    gitlab_runner.make(args.hostname, args.out)


def main():
    parser = argparse.ArgumentParser(prog='Open source software gitlab command tools')
    subs = parser.add_subparsers(dest='sub_command')

    def _common(x):
        x.add_argument('--url', required=True, help='Gitlab url')
        x.add_argument('--token', required=True, help='Gitlab access token')
        x.add_argument('--db', required=True,  help='Gitlab runner registered db')

    # Generate gitlab-ci config files.
    cmd = subs.add_parser('runner.register', help='Register gitlab-runner')
    cmd.add_argument('--url', required=True, help='Gitlab url')
    cmd.add_argument('--token', required=True, help='Gitlab runner registration token')
    cmd.add_argument('--db', required=True,  help='Gitlab runner registered db')
    cmd.add_argument('--count', default=1, type=int, help='')
    cmd.set_defaults(func=gitlab_runner_register)

    # Generate gitlab-ci reset.
    cmd = subs.add_parser('runner.reset', help='Register gitlab-runner')
    _common(cmd)
    cmd.add_argument('--hostname', default=None, help='')
    cmd.set_defaults(func=gitlab_runner_reset)

    cmd = subs.add_parser('runner.active', help='')
    _common(cmd)
    cmd.add_argument('--hostname', default=None, help='')
    cmd.set_defaults(func=gitlab_runner_active)

    cmd = subs.add_parser('runner.deactive', help='')
    _common(cmd)
    cmd.add_argument('--hostname', default=None, help='')
    cmd.set_defaults(func=gitlab_runner_deactive)

    # Generate gitlab-ci reset. kypLygrDSZ-92NewWx4R
    cmd = subs.add_parser('runner.config', help='Register gitlab-runner')
    _common(cmd)
    cmd.add_argument('--hostname', required=True,  help='')
    cmd.add_argument('--builder', type=int, default=0, help='')
    cmd.add_argument('--tester', type=int, default=0, help='')
    cmd.add_argument('--deployer', type=int, default=0, help='')
    cmd.add_argument('--trigger', type=int, default=0, help='')
    cmd.add_argument('--platform', required=True, help='')
    cmd.add_argument('--arch', default='adm64', help='')
    cmd.add_argument('--workbench', default=None, help='')
    cmd.set_defaults(func=gitlab_runner_config)

    cmd = subs.add_parser('runner.make', help='')
    _common(cmd)
    cmd.add_argument('--out', default="runner-config",  help='')
    cmd.add_argument('--hostname', required=True,  help='')

    cmd.set_defaults(func=gitlab_runner_make)

    args = parser.parse_args()
    return args.func(args)


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(e)
        sys.exit(1)

