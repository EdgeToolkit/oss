import os
import re
import sys
import argparse
from epm.utils import Jinja2, abspath

_DIR = os.path.dirname(abspath(__file__))
from configure import Synthesis


def gitlab_ci_generate(args):
    """generate gitlab ci config file
    """
    out_dir = abspath(args.out)
    synthesis = Synthesis('config.yml')
    context = {'synthesis': synthesis}
    docker_registry_url = os.getenv('DOCKER_REGISTRY_URL')
    if docker_registry_url:
        if not docker_registry_url.endswith('/'):
            docker_registry_url = '/'
        context['DOCKER_REGISTRY_URL'] = docker_registry_url

    j2 = Jinja2(f"{_DIR}/templates", context=context)
    if args.trigger:
        j2.render('trigger.yml.j2', outfile=f'{out_dir}/trigger.yml')
        print('Gitlab CI trigger config file generated.')
    if args.package:
        for name, package in synthesis.package.items():
            if '*' in args.package or name in args.package:
                print(f"[{name}] ...")
                j2.render('package.yml.j2', outfile=f'{out_dir}/{name}.yml',
                          context={'package': package})
                if not package.config.tool and package.tool_user:
                    j2.render('package.yml.j2', outfile=f'{out_dir}/{name}.tool.yml',
                              context={'package': package, 'FOR_TOOL': True})
    return None


def main():
    parser = argparse.ArgumentParser(prog='Open source software gitlab-ci command tools')
    subs = parser.add_subparsers(dest='sub_command')

    # Generate gitlab-ci config files.
    cmd = subs.add_parser('generate', help='Generate gitlab runner config')
    cmd.add_argument('--package', default=None, action='append', help='Generate package ci config file.')
    cmd.add_argument('--trigger', default=False, action='store_true', help='Generate gitlab-ci trigger file')
    cmd.add_argument('--out', default='.gitlab-ci/.cache', action='append',
                     help='Directory where generated file sotrage')

    cmd.set_defaults(func=gitlab_ci_generate)

    args = parser.parse_args()
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
