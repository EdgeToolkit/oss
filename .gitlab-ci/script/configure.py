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
import copy
import argparse
import pprint
import re
import networkx as nx
from collections import namedtuple
from epm.tools import create_requirements, create_build_tools
from epm.utils import abspath
from epm.model.project import Project

_DIR = os.path.dirname(abspath(__file__))

P_MSVC =re.compile(r'^(?P<name>vs20(17|19))d?$')
P_GCC=re.compile(r'^(?P<name>gcc\d(-x86|-armv7|-armv8)?)d?$')

class Package(object):
    MANIFEST = 'package.yml'

    def __init__(self, name, synthesis):
        self._synthesis = synthesis

        self._requirements = None
        self._build_requirements = None
        self._profile = None
        self._meta_info = None
        self._ctree = None
        self._ctree4tool = None

        self._config = None
        self._user = None
        self._tool_user = None
        self._script = None
        self.dir = abspath(f"{_DIR}/../../{name}")


    @property
    def meta_info(self):
        if self._meta_info is None:
            with open(f"{self.dir}/{self.MANIFEST}") as f:
                self._meta_info = yaml.safe_load(f) or {}
        return self._meta_info

    @property
    def version(self):
        return str(self.meta_info['version'])

    @property
    def name(self):
        return self.meta_info['name']

    @property
    def scheme(self):
        scheme = self.meta_info.get('scheme') or {}
        schemes = list(scheme.keys())
        schemes.sort()
        return schemes

    @property
    def program(self):
       
        program = []
        for p in self.meta_info.get('program') or []:
            e = p['name'] if isinstance(p, dict) else p
            program.append(e)

        return program

    @property
    def requirements(self):
        if self._requirements is None:
            self._requirements = create_requirements(self.meta_info)
        return self._requirements

    @property
    def build_requirements(self):
        if self._build_requirements is None:
            self._build_requirements = create_build_tools(self.meta_info)
        return self._build_requirements

    @property
    def config(self):
        if self._config is None:
            config = self._synthesis.config.package[self.name]

            tool = config.get('tool') or False
            repack = config.get('repack') or False
            profile = config.get('profile') or []

            program = config.get('program') or {}
            
            if not program and self.program:
                program = {'Windows': self.program[:1], 'Linux': self.program[:1]}
            print(self.name, '->', program)    
            
            self._config = namedtuple("Config", "tool repack profile program")(
                tool, repack, profile, program)
            
        return self._config

    def _used_by(self, tool=False, repack=False):
        graph = self._synthesis.holograph if tool else self._synthesis.graph
        result = set()
        for name in graph:
            if name == self.name:
                continue
            
            pkg = self._synthesis.package[name]            
            if pkg.config.tool:
                if nx.has_path(graph, name, self.name):
                    result.add(name)        
        return list(result)

    @property
    def user(self):
        if self._user is None:
            self._user = self._used_by()
        return self._user

    @property
    def tool_user(self):
        if self._tool_user is None:
            self._tool_user = self._used_by(tool=True)
        return self._tool_user

    @property
    def ctree(self):
        if self._ctree is None:
            tree = {}    
            for profile in self.config.profile:
                for scheme in self.scheme or ['None']:
                    project = Project(profile, scheme, directory=f'{self.name}')
                    if not project.available:
                        continue
                    name = None
                    msvc = P_MSVC.match(profile)
                    gcc = P_GCC.match(profile)
                    
                    if msvc:
                        name = 'MSVC'
                    for p in [P_GCC]:
                        m = p.match(profile)
                        if m:
                            name = m.group('name')
                            break
                    if name:
                        if name not in tree:
                            tree[name] = dict() 
                        if profile not in tree[name]:
                            tree[name][profile] = set()
                        if scheme in ['None', 'none', 'default']:
                            scheme='none'    
                        tree[name][profile].add(scheme)
            self._ctree = tree
            
        return self._ctree

    @property
    def ctree4tool(self):
        if self._ctree4tool is None:            
            tree = {}
            for name in self.tool_user:
                pkg = self._synthesis.package[name]
                if not pkg.config.tool:
                    continue
                
                for group, config in pkg.ctree.items():                    
                    c = tree[group] if group in tree else {}
                    for profile, schemes in config.items():
                        if profile not in c:
                            c[profile] = schemes
                        else:
                            c[profile].update(schemes)
                    if c:
                        tree[group] = c
            self._ctree4tool = tree
        return self._ctree4tool

class Config(object):
    def __init__(self, filename):
        self.__file__ = abspath(filename)
        assert os.path.exists(self.__file__)
        self._package = None
        with open(self.__file__) as f:
            self._data = yaml.safe_load(f) or []        
        self._base = self._data[0]

    def __contains__(self, name):
        return name in self.data

    @property
    def package(self):
        if self._package is None:
            self._package = self._parse()
        return self._package

    @property
    def version(self):
        return self._base.get('version')
    @property
    def workbench(self):
        return self._base.get('workbench', None) or None
        
    def _parse(self):
        base = self._parse_config(self._base)

        package = {}
        for conf in self._data[1:]:
            conf = conf if isinstance(conf, dict) else {'name': conf}
            name = conf['name']
            package[name] = self._parse_config(conf, base)
        return package

    @staticmethod
    def _expand_profile(prc):
        def _expand(l):
            if isinstance(l, str):
                return [l]
            result = []
            for i in l:
                result += _expand(i)
            return result
        return _expand(prc or [])

    @staticmethod
    def _profile_expr(c):
        config = set(Config._expand_profile(c))

        pattern = re.compile(r'(?P<name>[\w\/\.\-]+)\s*(\{(?P<kind>.*)\}(?P<suffix>[\w\-]+)?)?')
        profiles = set()
        for expr in config:

            m = pattern.match(expr)
            name = m.group('name')
            kind = m.group('kind') or ""
            suffix = m.group('suffix') or ""

            for i in kind.split('|'):
                pr = name + i.strip() + suffix
                profiles.add(pr)
        return profiles

    @staticmethod
    def _parse_config(config, base={}):

        config = config or {}
        result = dict(base, **config)
        result.pop('profile', None)
        result.pop('+profile', None)
        result.pop('-profile', None)
        if 'profile' in config:
            profile = Config._profile_expr(config['profile'])
        else:
            profile = set(base.get('profile') or [])
            profile = profile.difference(Config._profile_expr(config.get('-profile')))
            profile = profile.union(Config._profile_expr(config.get('+profile')))

        result['profile'] = profile
        for i in ['name', 'version', 'tool', 'repack']:
            if i in config:
                result[i] = config[i]
        program = config.get('program', None)
        if program:
            if isinstance(program, (str)):
                program = {'Windows': [program], 'Linux': [program]}
            elif isinstance(program, dict):
                prog = {}
                for platform, value in program.items():
                    prog[platform] = [value] if isinstance(value, str) else value
                program = prog
            elif isinstance(program, list):
                program = {'Windows': program, 'Linux': program}
            result['program'] = program


        return result


class Synthesis(object):

    def __init__(self, filename=None):
        filename = filename or f"{_DIR}/../config.yml"
        self._filename = abspath(filename)
        self._config = None
        self._package = None
        self._graph = None
        self._holograph = None

        self._layout = None
        self._tool_layout = None

    @property
    def filename(self):
        return self._filename

    @property
    def config(self):
        if self._config is None:
            self._config = Config(self.filename)
        return self._config

    @property
    def package(self):
        if self._package is None:
            self._package = {}
            for name in self.config.package:
                pkg = Package(name, self)
                if pkg.config.repack:
                    continue
                self._package[name] = pkg
        return self._package

    @property
    def version(self):
        return self.config.version

    @property
    def graph(self):
        """package (not include build tool) graph
        """
        if self._graph is None:
            self._graph = nx.DiGraph()
            for name, pkg in self.package.items():
                if pkg.config.tool:
                    continue
                self._graph.add_node(name)

            for name in self._graph: #self.package.items():
                pkg = self.package[name]
                for _, detail in pkg.requirements.items():
                    ref = detail.ref
                    pkg = self.package[ref.name]
                    if str(ref.version) == str(pkg.version):
                        self._graph.add_edge(name, pkg.name)
                    else:
                        print(f"{name} require {detail} but {pkg.name}/{pkg.version} in bundle.")
        return self._graph

    @property
    def holograph(self):
        """package (include build tools) graph
        """
        if self._holograph is None:
            self._holograph = nx.DiGraph()
            for name, pkg in self.package.items():
                self._holograph.add_node(name)

            for name, pkg in self.package.items():
                for requirements in [pkg.requirements, pkg.build_requirements]:
                    for _, detail in requirements.items():
                        ref = detail.ref
                        if ref.name not in self.package:
                            continue
                        pkg = self.package[ref.name]
                        if str(ref.version) == str(pkg.version):
                            self._holograph.add_edge(name, pkg.name)
                        else:
                            print(f"{name} require {detail} but {pkg.name}/{pkg.version} in bundle.")
            if 'protoc' in self._holograph:
                self._holograph.remove_edge('protobuf', 'protoc')
        return self._holograph

    @property
    def layout(self):
        if self._layout is None:
            self._layout = self._layout_analyze(self.graph)
        return self._layout

    @property
    def tool_layout(self):

        if self._tool_layout is None:
            self._tool_layout = []
            packages = set()
            for name, pkg in self.package.items():
                
                if not pkg.config.tool:
                    continue
                packages.add(name)  
                for requirements in [pkg.requirements, pkg.build_requirements]:
                    for _, detail in requirements.items():
                        packages.add(detail.ref.name)

            for layer in self._layout_analyze(self.holograph):
                layer = set(layer).intersection(packages)
                if layer:
                    self._tool_layout.append(layer)
        return self._tool_layout

    @staticmethod
    def _layout_analyze(graph):
        graph = copy.deepcopy(graph)

        def _analyze(g, result):
            layer = set()
            for name, deps in g.items():
                if not deps:
                    layer.add(name)
            if layer:
                result.append(layer)
                [g.pop(i) for i in layer]
                for name, deps in g.items():
                    for it in result:
                        deps -= it
            if not g:
                return result
            return _analyze(g, result)

        group = {k: set(graph.neighbors(k)) for k in graph.nodes()}
        layout = _analyze(group, [])        
        return layout

    def dump(self):
        folder = ".epm/bundle-dump"
        from conans.tools import mkdir, rmdir
        rmdir(folder)
        mkdir(folder)

        def _dump(name, data):
            with open(f"{folder}/{name}.yaml", 'w') as f:
                yaml.safe_dump(data, f)

        _dump("layout", {'layout': self.layout, 'tool-layout': self.tool_layout})
        data = {}
        for name, pkg in self.package.items():
            data[name] = vars(pkg) #.as_dict()
        _dump("packages", data)


def main():
    manager = Synthesis()
    manager.dump()


if __name__ == '__main__':
    sys.exit(main())
