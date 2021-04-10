#!/usr/bin/env python3
import os
import re
import sys
import argparse
from collections import namedtuple
from epm.utils import Jinja2, abspath

_DIR = os.path.dirname(abspath(__file__))
_TOP = abspath(f"{_DIR}/../..")
from configure import Synthesis

P_MSVC =re.compile(r'^(?P<name>vs20(17|19))(?P<arch>(-x86))?d?$')
P_GCC=re.compile(r'^(?P<name>gcc\d)(-(?P<arch>(x86|armv7|armv8)))?d?$')

_IMAGES = {
    'gcc5': 'ubuntu:xenial', 
    'gcc6': 'ubuntu:xenial', 
    'gcc7': 'ubuntu:xenial', 
    'gcc8': 'ubuntu:bionic',    
}
def _make_matrix(group, config):
    P = set(config.keys())
    S = set()
    for s in config.values():
        S.update(s)

    arch = 'x86_64'
    image = None
    if group == 'MSVC':
        compiler = 'MSVC'
    else:
        gcc = P_GCC.match(group)
        arch = gcc.group('arch') or 'x86_64'
        compiler = 'gcc'
        
        image = _IMAGES.get(group) or None
    matrix = namedtuple('CMatrix', 'profile scheme group arch compiler image'
    )(P, S, group, arch, compiler, image)
    return matrix

def _ctree_matrix(ctree, group=None):
    matrix = []
    if group:
        return _make_matrix(group, ctree[group])
    else:
        for group, config in ctree.items():
            matrix.append(_make_matrix(group, config))
    return matrix

def _ctree_matrix_scheme(ctree, compiler=None, arch=None):
    schemes = set()
    for m in _ctree_matrix(ctree):
        match = True
        if compiler and compiler != m.compiler:
            match = False
        if arch and arch != m.arch:
            match = False
        if match:
            schemes.update(m.scheme)
    return schemes

def gitlab_ci_generate(args):
    """generate gitlab ci config file
    """
    out_dir = abspath(args.out)
    synthesis = Synthesis()
    context = {'synthesis': synthesis, 'workbench': 'Z1'}
    docker_registry_url = os.getenv('DOCKER_REGISTRY_URL')
    if docker_registry_url:
        if not docker_registry_url.endswith('/'):
            docker_registry_url = '/'
        context['DOCKER_REGISTRY_URL'] = docker_registry_url

    
    if args.trigger:
        j2 = Jinja2(f"{_DIR}/templates", context=context)
        j2.render('tools.yml.j2', outfile=f'{out_dir}/tools.yml')
        j2.render('packages.yml.j2', outfile=f'{out_dir}/packages.yml')

        print('Gitlab CI trigger config file generated.')

    if args.package:
        j2 = Jinja2(f"{_DIR}/templates/config", context=context)
        j2.Filters['cmatrix'] = _ctree_matrix
        j2.Filters['scheme_filter'] = _ctree_matrix_scheme
        for name, package in synthesis.package.items():
            if 'all' in args.package or name in args.package:                
                print(f"[{name}] ...")
                j2.render('package.yml.j2', outfile=f'{out_dir}/{name}.yml',
                    context={'package': package})
                if not package.config.tool and package.tool_user:
                    j2.render('package4tool.yml.j2', outfile=f'{out_dir}/{name}.tool.yml',
                        context={'package': package})

    return None


def main():
    parser = argparse.ArgumentParser(prog='Open source software gitlab-ci command tools')
    subs = parser.add_subparsers(dest='sub_command')

    # Generate gitlab-ci config files.
    cmd = subs.add_parser('generate', help='Generate gitlab runner config')
    cmd.add_argument('--package', default=None, action='append', help='Generate package ci config file.')
    cmd.add_argument('--trigger', default=False, action='store_true', help='Generate gitlab-ci trigger file')
    cmd.add_argument('--out', default='.gitlab-ci/.cache', help='Directory where generated file sotrage')

    cmd.set_defaults(func=gitlab_ci_generate)

    args = parser.parse_args()
    args.out = abspath(args.out)
    from conans.tools import chdir
    with chdir(_TOP):
        return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
