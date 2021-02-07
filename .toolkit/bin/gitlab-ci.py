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


    args = parser.parse_args()
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
