import os
import re
import sys
import argparse
from epm.utils import Jinja2, abspath

_DIR = os.path.dirname(abspath(__file__))
_LIBD = abspath(f"{_DIR}/../lib")
sys.path.insert(0, _LIBD)
from configure import Synthesis
from ci import GitlabRunner


def gitlab_ci_generate(args):
    """generate gitlab ci config file
    """
    target = args.target or ['trigger']
    filename = 'config.yml'
    synthesis = Synthesis(filename)
    context = {'synthesis': synthesis}
    docker_registry_url = os.getenv('DOCKER_REGISTRY_URL')
    if docker_registry_url:
        if not docker_registry_url.endswith('/'):
            docker_registry_url = '/'
        context['DOCKER_REGISTRY_URL'] = docker_registry_url

    j2 = Jinja2(f"{_LIBD}/templates/.gitlab-ci", context=context)
    if 'trigger' in target:
        j2.render('trigger.yml.j2', outfile=f'.gitlab-ci/cache/trigger.yml')
        print('Gitlab CI trigger config file generated.')
    if 'package' in target:
        for name, package in synthesis.package.items():
            print(f"[{name}] ...", end=' ')
            j2.render('package.yml.j2', outfile=f'.gitlab-ci/cache/{name}.yml',
                      context={'package': package})
            if not package.config.tool and package.tool_user:
                print(f"{name}.tool ...", end='')
                j2.render('package.yml.j2', outfile=f'.gitlab-ci/cache/{name}.tool.yml',
                          context={'package': package, 'FOR_TOOL': True})
            print(" done.")
    return None


def gitlab_runner_register(args):
    gitlab_runner = GitlabRunner(args.url, args.dir, registration=args.token)
    gitlab_runner.register(args.count)


def gitlab_runner_reset(args):

    gitlab_runner = GitlabRunner(args.url, args.dir, access=args.token)
    gitlab_runner.reset(args.hostname)


def gitlab_runner_config(args):
    gitlab_runner = GitlabRunner(args.url, args.dir, access=args.token)
    gitlab_runner.config(args.hostname, workbench=args.workbench,
                         builder=args.builder, tester=args.tester,
                         deployer=args.deployer, trigger=args.trigger,
                         platform=args.platform, arch=args.arch)


def gitlab_runner_active(args):
    gitlab_runner = GitlabRunner(args.url, args.dir, access=args.token)
    gitlab_runner.active(not args.disable)


def gitlab_runner_make(args):
    gitlab_runner = GitlabRunner(args.url, args.dir, access=args.token)
    gitlab_runner.make(args.hostname, args.out)


def main():
    parser = argparse.ArgumentParser(prog='Open source software gitlab command tools')
    subs = parser.add_subparsers(dest='sub_command')

    # Generate gitlab-ci config files.
    cmd = subs.add_parser('generate', help='Generate gitlab runner config')
    cmd.add_argument('--target', default=None, action='append', help='Generate config for bundle')
    cmd.set_defaults(func=gitlab_ci_generate)

    # Generate gitlab-ci config files.
    cmd = subs.add_parser('runner.register', help='Register gitlab-runner')
    cmd.add_argument('--url', required=True, help='Gitlab url')
    cmd.add_argument('--token', required=True, help='Gitlab runner registration token')
    cmd.add_argument('--dir', required=True,  help='Directory where store token and runner log')
    cmd.add_argument('--count', default=1, type=int, help='')
    cmd.set_defaults(func=gitlab_runner_register)

    # Generate gitlab-ci reset.
    cmd = subs.add_parser('runner.reset', help='Register gitlab-runner')
    cmd.add_argument('--url', required=True, help='Gitlab url')
    cmd.add_argument('--token', required=True, help='Gitlab access private token')
    cmd.add_argument('--hostname', default=None, help='')
    cmd.add_argument('--dir', required=True,  help='Directory where store token and runner log')
    cmd.set_defaults(func=gitlab_runner_reset)

    cmd = subs.add_parser('runner.active', help='Register gitlab-runner')
    cmd.add_argument('--url', required=True, help='Gitlab url')
    cmd.add_argument('--token', required=True, help='Gitlab access private token')
    cmd.add_argument('--dir', required=True,  help='Directory where store token and runner log')
    cmd.add_argument('--disable', default=False, action='store_true', help='')
    cmd.set_defaults(func=gitlab_runner_active)

    # Generate gitlab-ci reset. kypLygrDSZ-92NewWx4R
    cmd = subs.add_parser('runner.config', help='Register gitlab-runner')
    cmd.add_argument('--url', required=True, help='Gitlab url')
    cmd.add_argument('--token', required=True, help='Gitlab access private token')
    cmd.add_argument('--dir', required=True,  help='Directory where store token and runner log')
    cmd.add_argument('--hostname', required=True,  help='')
    cmd.add_argument('--builder', type=int, default=0, help='')
    cmd.add_argument('--tester', type=int, default=0, help='')
    cmd.add_argument('--deployer', type=int, default=0, help='')
    cmd.add_argument('--trigger', type=int, default=0, help='')
    cmd.add_argument('--platform', required=True, help='')
    cmd.add_argument('--arch', default='adm64', help='')
    cmd.add_argument('--workbench', default=None, help='')
    cmd.set_defaults(func=gitlab_runner_config)

    cmd = subs.add_parser('runner.make', help='Register gitlab-runner')
    cmd.add_argument('--url', required=True, help='Gitlab url')
    cmd.add_argument('--token', required=True, help='Gitlab access private token')
    cmd.add_argument('--dir', required=True,  help='Directory where store token and runner log')
    cmd.add_argument('--out', default="runner-config",  help='')

    cmd.set_defaults(func=gitlab_runner_make)

    args = parser.parse_args()
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
