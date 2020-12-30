#!/usr/bin/env python3
import os
import sys
import re
import yaml
import tempfile   
import copy
import pathlib
import glob
import time
import hashlib
import base64
import shutil
import subprocess
import argparse
import pprint
import networkx as nx


from collections import OrderedDict, namedtuple
from conans.tools import mkdir, rmdir, chdir, ConanOutput
from epm.tools import create_requirements, create_build_tools
from utils import ancestor, descendant, difference, intersection, epm_command, DepGraph, jinja_render
from utils import ObjectView


_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOTDIR = os.path.normpath(f"{_DIR}/../../..")


def _set(x):
    if isinstance(x, str):
        return {x}
    return set(x or [])


def _parse_profile_expr(config):
    config = _set(config)
    Pattern = re.compile(r'(?P<name>\w[\w\/\.\-]+)\s*(\{(?P<suffix>.*)\})?')
    profiles = set()
    for expr in config:
        m = Pattern.match(expr)
        name = m.group('name')
        suffix = m.group('suffix') or ""
        profiles.add(name)
        for i in suffix.split('|'):
            profiles.add(name + i.strip())
    return profiles


class _Base(object):
    MANIFEST = None

    def __init__(self, direcotry=None, out=None):
        self.dir = os.path.abspath(direcotry or '.')
        self._metainfo = None
        self.out = out or ConanOutput(sys.stdout, color=True)
        self.info = self.out.info
        self.highlight = self.out.highlight
        self.warn = self.out.warn
        self.error = self.out.error

    @property
    def metainfo(self):
        if self._metainfo is None:
            if self.MANIFEST:
                path = os.path.join(self.dir, self.MANIFEST)
                with open(path) as f:
                    self._metainfo = yaml.safe_load(f)
            self._metainfo = self._metainfo or {}
        return self._metainfo

class MetaInfo(_Base):
    MANIFEST = 'bundle.yml'

    def __init__(self, dir, out=None):
        super().__init__(dir, out)
        self._settings = self.metainfo.pop('.meta-info', {})
        profile = _parse_profile_expr(self._settings.get('profile'))
        self._settings['profile'] = profile
        self._bundle = None

    @property
    def bundle(self):
        if self._bundle is None:
            self._bundle = self._parse()
        return self._bundle

    def find_package(self, name):
        for _, bundle in self.bunlde.items():
            if name in bundle:
                return bundle[name]
        return None

    def _parse(self):
        bundles = {}
        PackageMetaInfo = namedtuple('PackageMetaInfo', ['name', 'profile', 'tool', 'redist'])
        for bundle_name, packages in self.metainfo.items():            
            bundle = {}
            settings, packages = self._bundle_preprocess(packages)
            for config in packages:
                name, this = self._parse_bundle_package(config, settings)
                bundle[name] = PackageMetaInfo(name, this['profile'],
                this.get('tool') or False, this.get('redist') or False, )
            bundles[bundle_name] = bundle
        return bundles

    @staticmethod
    def merge_settings(config, template):
        config = config or {}
        result = dict(template, **config)
        result.pop('profile', None)
        result.pop('+profile', None)
        result.pop('-profile', None)
        if 'profile' in config:
            profile = _parse_profile_expr(config['profile'])
        else:
            profile = template.get('profile') or set()
            profile = profile.difference(_parse_profile_expr(config.get('-profile')))
            profile = profile.union(_parse_profile_expr(config.get('+profile')))
            
        result['profile'] = profile
        return result

    def _bundle_preprocess(self, packages):
        settings = None
        pkg = []
        for config in packages:
            if isinstance(config, dict):
                if 'name' not in config:
                    assert settings is None
                    settings = config
                    continue
            pkg.append(config)
        return settings, pkg

    def _parse_bundle_package(self, config, bundle_settings):
        pkg_settings = config if isinstance(config, dict) else {}
        name = config if isinstance(config, str) else config['name']
        
        settings = self.merge_settings(bundle_settings, self._settings)
        settings = self.merge_settings(pkg_settings, settings)
        return name, settings



class Package(_Base):
    MANIFEST = 'package.yml'

    def __init__(self, directory, out=None, settings=None):
        super().__init__(directory, out)
        self.settings = settings

    @property
    def version(self):
        return self.metainfo['version']

    @property
    def name(self):
        return self.metainfo['name']

    @property
    def scheme(self):
        return set(self.metainfo.get('scheme') or [])

    @property
    def requirements(self):
        return create_requirements(self.metainfo)

    @property
    def build_tools(self):
        return create_build_tools(self.metainfo)


def package_graph(packages, outside=False):
    graph = nx.DiGraph()
    for pkg in packages:
        graph.add_node(pkg.name)

    for pkg in packages:
        for dep in pkg.requirements:
            if dep in packages or outside:
                graph.add_edge(pkg.name, dep)
    return graph


class Holograph(_Base):

    def __init__(self,dir=_ROOTDIR, out=None):
        super().__init__(dir, out)
        self.settings = MetaInfo(dir, out)
        self._package = None
        self._bundle = None

    @property
    def package(self):
        if self._package is None:
            self._package = {}
            for _, bundle in self.settings.bundle.items():
                for name, settings in bundle.items():
                    self._package[name] = Package(os.path.join(self.dir, name), self.out, settings=settings)
        return self._package

    @property
    def bundle(self):
        if self._bundle is None:
            self._bundle = {}
            for name, bundle in self.settings.bundle.items():
                self._bundle[name] = {}
                for pkg_name in bundle:
                    self._bundle[name][pkg_name] = self.package[pkg_name]
        return self._bundle            

    @property
    def graph(self):
        if self._graph is None:
            self._graph = package_graph(self.package)
        return self._graph


class Bundle(_Base):

    def __init__(self, name, holograph):
        super().__init__(holograph.dir, holograph.out)
        self.name = name
        self.holograph = holograph
        assert name in holograph.settings.bundle
        self.settings = holograph.settings.bundle[name]

        self._package = None
        self._graph = None

        self._tool = None
        self._tgraph = None

        self._property = None
    
    @property
    def package(self):
        if self._package is None:
            bundle = self.holograph.bundle[self.name]
            self._package = {k: v for k, v in bundle.items() if not v.settings.tool}
        return self._package

    @property
    def tool(self):
        if self._tool is None:
            bundle = self.holograph.bundle[self.name]
            self._tool = {k: v for k, v in bundle.items() if v.settings.tool}
        return self._tool

    @property
    def graph(self):
        if self._graph is None:
            self._graph = nx.DiGraph()
            for name, pkg in self.package.items():
                self._graph.add_node(name)

            for name, pkg in self.package.items():
                for dep in pkg.requirements:
                    self._graph.add_edge(name, dep)
        return self._graph

    @property
    def tgraph(self):
        if self._tgraph is None:
            self._tgraph = nx.DiGraph()
            for name in self.tool:
                self._tgraph.add_node(name)

            for name, pkg in self.tool.items():
                for dep in pkg.requirements:
                    self._tgraph.add_edge(name, dep)

                for dep in pkg.build_tools:
                    self._tgraph.add_edge(name, dep)

        return self._tgraph

    def layout(self, tool=False, out_boundle=False):
        graph = self.tgraph if tool else self.graph
        DG = DepGraph(graph)
        layout = []

        for layer in DG.layout:
            l = []
            for name in layer:
                mine = name in self.package or name in self.tool
                if mine or out_boundle:
                    l.append(name)
            if l:
                layout.append(l)
        return layout

    def used_by(self, name, tool=False):
        """ return the package which depend on the $name package
        """
        graph = self.tgraph if tool else self.graph
        pkg = self.tool if tool else self.package
        print(tool, graph.nodes())
        print(list(pkg))
        result = set()
        for i in pkg:
            if i == name: continue            
            if nx.has_path(graph, i , name):
                result.add(i)
        return result


_CI_CONFIG_HEADER = """
stages:
  - build
  - test
  - deploy
"""


def _generate_pacakge_configure(bundle, name, toollib=False):
    pkg = bundle.package[name] if name in bundle.package else bundle.tool[name]
    context = {'bundle': bundle, 'name': name,
        'tags': [f"{bundle.name}@OSS"]}
    profiles = set() if toollib else pkg.settings.profile
    schemes = set() if toollib else pkg.scheme

    if toollib:
        for i in bundle.used_by(pkg.name, tool=True):
            tool = bundle.tool[i]
            profiles |= set(tool.settings.profile)            
            schemes |= set(tool.scheme)
    schemes = schemes or  [None]

    content = _CI_CONFIG_HEADER
    for profile in profiles:
        for scheme in schemes:
            cname = f"{profile}@{scheme}" if scheme else profile
            ctx = dict(context, profile=profile, scheme=scheme, cname=cname)
            if profile.startswith('vs20'):
                content += jinja_render(ctx, 'gitlab-ci/MSVC.yml.j2') + "\n"
            if profile.startswith('gcc'):
                MAP = {'epmkit/gcc5': ['gcc5', 'gcc5d'], 'epmkit/gcc5-x86': ['gcc5-x86', 'gcc5-x86d'],
                'epmkit/gcc8': ['gcc8', 'gcc5d'], 'epmkit/gcc8-x86': ['gcc8-x86', 'gcc8-x86d']}
                for image, pr in MAP.items():
                    if profile in pr:
                        break
                from epm.model.profile import Profile
                pr = Profile(profile, None)
                ctx.update({'image': image, 'docker': pr.docker})
                content += jinja_render(ctx, 'gitlab-ci/GCC.yml.j2') + "\n"    
    folder = os.path.join(".gitlab-ci", "bootstrap" if toollib else "")
    mkdir(folder)
    with open(os.path.join(folder, f"{pkg.name}.yml"), 'w') as f:
        f.write(content)


def gitlab_ci(args, out):
    holograph = Holograph()
    name = args.bundle
    if not name:
        import git
        repo = git.Repo('.')
        name = repo.active_branch.name.split('/')[0]

    bundle = Bundle(name, holograph)
    context = {'bundle': bundle}
    jinja_render(context, "gitlab-ci/.gitlab-ci.yml.j2", '.gitlab-ci/.main.yml')

    bundle = Bundle(name, holograph)

    for name in bundle.package:
        _generate_pacakge_configure(bundle, name)
        if name in bundle.tgraph.nodes():
            _generate_pacakge_configure(bundle, name, True)

    for name in bundle.tool:
        _generate_pacakge_configure(bundle, name)


class _Builder(object):

    def __init__(self, args, out):
        self._args = args
        self.name = args.name[0]
        self.out = out
        self.holo = Holograph()
        self.bundle = Bundle(self.name, self.holo)
        self._build_record_filename = os.path.join(_ROOTDIR, ".epm/bundle-built.yml")
        self._build_record = []
        if os.path.exists(self._build_record_filename):
            try:
                with open(self._build_record_filename) as f:
                    self._build_record = yaml.safe_load(f) or []
            except:
                pass

    def _build(self, packages):

        command = ['epm', '-p', self._args.profile]
        if self._args.scheme:
            command += ['-s', self._args.scheme]
        create_cmd= command + ['create']
        upload_cmd= command + ['upload']
        n = len(packages)
        i = 0
        for name in packages:
            
            def _run(cmd):
                print(f"[{i+1}/{n}  {name} ]", " ".join(cmd))
                if self._args.dry_run:
                    return True
                wd = os.path.join(_ROOTDIR, name)
                proc = subprocess.run(cmd, cwd=wd)
                if proc.returncode:
                    self.out.error("Build package {name} failed.")
                    return False                
                return True

            print(f"[{i+1}/{n}  {name} ]", " ".join(create_cmd))
            if not _run(command + ['create']):
                break
            if self._args.remote:
               if not _run(command + ['upload', '--remote', self._args.remote]):
                   break
                   
            if not self._args.dry_run:
                self._build_record.append(name)
            i += 1
        mkdir(os.path.dirname(self._build_record_filename))
        with open(self._build_record_filename, "w") as f:
            yaml.safe_dump(self._build_record, f)
        return n-i

    def _run(self, scheme=None):
        layouts = self.bundle.layout(self._args.tool)
        packages = []
        for layout in layouts:
            for name in layout:
                pkg = self.holo.package[name]
                if name in self._build_record:
                    self.out.info(f"Skip package {pkg.name} as it already in in build record file")
                    continue

                if pkg.settings.redist and not self._args.with_redist:
                    self.out.info(f"Skip redist package {pkg.name}")
                    continue
                if self._args.profile not in pkg.settings.profile:
                    self.out.info(f"Skip {pkg.name}, because of unsupported profile.")
                    continue
                if scheme and scheme not in pkg.scheme:
                    self.out.info(f"Skip {pkg.name}, because of unsupported scheme <{scheme}>.")
                    continue


                packages.append(name)
        self.out.highlight("-- {} packages to build".format(len(packages)))
        self.out.highlight("-- " + " ".join(packages))
        return self._build(packages)


    @staticmethod
    def run(args, out, scheme=None):
        return _Builder(args, out)._run(scheme=args.scheme)

_WORKBENCH="""
workbench:
  name: {{bundle.name}}

conan:
  storage: ${workbench}/data
  remotes:
  - name: {{bundle.name}}
    url: {{bundle.remote}}
{% for b in reverse(bundles) -%}
  - name: {{b.name}}
    url: {{b.remote}}
{%- if b.name == bundle.name -%}
{%- break %}
{%- endif -%}    
{% endfor -%}

environment:
  EPM_MIRROR_MSYS2: {{config.environment.EPM_MIRROR_MSYS2}}

"""
class _Workbench(object):

    def __init__(self, args, out):
        self._args = args
        self.out = out
        with open(os.path.expanduser(args.config)) as f:
            data = yaml.safe_load(f)
        self.config = ObjectView(data)

    def generate(self, out=".workbench"):
        for bundle in self.config.bundle:
            if not self._args.bundle or bundle.name in self._args.bundle:
                context ={"bundle": bundle, "config": self.config, "bundles": list(reversed(self.config.bundle))}
                mkdir(f"{out}/{bundle.name}")
                jinja_render(context, 'workbench/config.yml.j2', f"{out}/{bundle.name}/config.yml")

    @staticmethod
    def run(args, out):
        workbench = _Workbench(args,out)
        workbench.generate()




def main():
    parser = argparse.ArgumentParser(prog='Open Source Software (for EdgeOS) bundle command tool.')
    subs = parser.add_subparsers(dest='cmd')

    subcmd = subs.add_parser('build', help='')

    subcmd.add_argument('name', nargs=1, type=str, help='name of the bundle to build.')

    subcmd.add_argument('--profile', type=str, required=True, help='Profile to build for')
    subcmd.add_argument('--scheme', default=None, type=str, help='Scheme of the packages to build')
    subcmd.add_argument('--remote', default=None, help='Conan remote repo name to upload')
    subcmd.add_argument('--console', default=False, action='store_true',
                        help='Print to console or to file(default to file')
    subcmd.add_argument('--dry-run', default=False, action='store_true', help='dry run ')
    subcmd.add_argument('--tool', default=False, action='store_true',
                        help='If set only build tools instead of package')
    subcmd.add_argument('--with-redist', default=False, action='store_true',
                         help='Build redist package or not.')

    subs.add_parser('gitlab-ci', help='Generate Gitlab-CI configure in .gitlab-ci folder.')

    subcmd = subs.add_parser('workbench', help='Generate workbench.')
    subcmd.add_argument('bundle', nargs='*', type=str, help='name of the bundle, if not set generate all.')
    subcmd.add_argument('-c', '--config', default="~/config/gitlab-ci/config.yml", type=str,
                        help='config file for the workbench retrieve requested information.')


    args = parser.parse_args()
    out = ConanOutput(sys.stdout, color=True)

    commands = {'build': _Builder.run,
                'gitlab-ci': gitlab_ci,
                'workbench': _Workbench.run}

    if args.cmd not in commands:
        out.error(f'{args.cmd} not exits. valid command ' + " ".join(list(commands)))
        return 1

    code = commands[args.cmd](args, out)
    sys.exit(code)


















def _show():
    holograph = Holograph()
    bundle = Bundle('toolset', holograph)
    print('------------- toolset ---------------')
    pprint.pprint(bundle.layout(tool=True, out_boundle=True))
    print('------------- base ---------------')
    bundle = Bundle('base', holograph)
    pprint.pprint(bundle.layout())
    print('-- TOOL --------------------------')
    pprint.pprint(bundle.layout(tool=True))
    print('protobuf used by', bundle.used_by('protobuf', tool=True))
if __name__ == '__main__':
    main()
    #_show()
