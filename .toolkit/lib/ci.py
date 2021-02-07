import os
import re
import sys
import argparse
from collections import namedtuple
import gitlab
from conans.tools import mkdir

from epm.utils import Jinja2, abspath
from configure import Synthesis

_DIR = os.path.dirname(abspath(__file__))


class Gitlab(object):

    def __init__(self):
        pass

    @staticmethod
    def command_generate(args):
        target = args.target or ['trigger']
        filename = 'config.yml'
        synthesis = Synthesis(filename)
        context = {'synthesis': synthesis, 'parallel_matrix': Gitlab._parallel_matrix,
                   'Combination': Gitlab._get_combination, 'Matrix': Gitlab._matrix}
        docker_registry_url = os.getenv('DOCKER_REGISTRY_URL')
        if docker_registry_url:
            if not docker_registry_url.endswith('/'):
                docker_registry_url = '/'
            context['DOCKER_REGISTRY_URL'] = docker_registry_url

        j2 = Jinja2(f"{_DIR}/templates/.gitlab-ci", context=context)
        if 'trigger' in target:
            j2.render('trigger.yml.j2', outfile=f'.gitlab-ci/cache/trigger.yml')
        if 'package' in target:
            for name, package in synthesis.package.items():
                j2.render('package.yml.j2', outfile=f'.gitlab-ci/cache/{name}.yml',
                          context={'package': package})
                if not package.config.tool and package.used_by(tool=True):
                    j2.render('package.yml.j2', outfile=f'.gitlab-ci/cache/{name}.tool.yml',
                              context={'package': package, 'FOR_TOOL': True})

    @staticmethod
    def _get_combination(package, tool=False):

        def _matrix(pat):
            if isinstance(pat, str):
                pat = re.compile(pat)
            matrix = package.matrix4tool if tool else package.matrix
            profiles = {}
            schemes = []
            for pr, s in matrix.items():
                if re.match(pat, pr):
                    if s not in schemes:
                        schemes.append(s)
                    index = schemes.index(s)
                    if index not in profiles:
                        profiles[index] = set()
                    profiles[index].add(pr)
            return [(prs, schemes[i]) for i, prs in profiles.items()]
        mat = {}
        for i in [5, 6, 7, 8]:
            for j in ['', '-x86', '-armv7', '-armv8']:
                mat[f"gcc{i}"] = r'^gcc{}{}\w*$'.format(i,j)
        for i in [100, 200]:
            mat[f"himix{i}"] = r'^himix{}\w*$'.format(i)
        for i in [300, 400]:
            mat[f"hisiv{i}"] = r'^hisiv{}\w*$'.format(i)
        for i in [2019]:
            mat[f"vs{i}"] = r'^vs20\d\d\w*$'

        matrix = {}
        for profile, pattern in mat.items():
            m = _matrix(pattern)
            if m:
                matrix[profile] = m
        return matrix

    @staticmethod
    def _matrix(combo, pattern):
        pattern = re.compile(pattern)
        matrix = []
        for profile, schemes in combo.items():
            if pattern.match(profile):
                for p, s in matrix:
                    if s == schemes:
                        p.add(profile)
                        break
                else:
                    matrix.append(({profile}, schemes))
                    print('*', matrix)

        return matrix


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

    j2 = Jinja2(f"{_DIR}/templates/.gitlab-ci", context=context)
    if 'trigger' in target:
        j2.render('trigger.yml.j2', outfile=f'.gitlab-ci/cache/trigger.yml')
    if 'package' in target:
        for name, package in synthesis.package.items():
            j2.render('package.yml.j2', outfile=f'.gitlab-ci/cache/{name}.yml',
                      context={'package': package})
            if not package.config.tool and package.tool_user:
                j2.render('package.yml.j2', outfile=f'.gitlab-ci/cache/{name}.tool.yml',
                          context={'package': package, 'FOR_TOOL': True})

def main():
    parser = argparse.ArgumentParser(prog='Open source software gitlab command tools')
    subs = parser.add_subparsers()

    # gitlab
    cmd = subs.add_parser('generate', help='Generate gitlab runner config')
    cmd.add_argument('--target', default=None, action='append', help='Generate config for bundle')
    cmd.set_defaults(func=gitlab_ci_generate)

    args = parser.parse_args()
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())