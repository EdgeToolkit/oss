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


from collections import OrderedDict, namedtuple
from conans.tools import mkdir, rmdir, chdir, ConanOutput
from epm.tools import create_requirements, create_build_tools
from epm.utils import ObjectView, sequence_cast
from epm.utils import abspath
from epm.model.project import Project

_DIR = os.path.dirname(abspath(__file__))


class Package(object):
    MANIFEST = 'package.yml'

    def __init__(self, name, synthesis):
        self._synthesis = synthesis

        self._requirements = None
        self._build_requirements = None
        self._profile = None
        self._meta_info = None

        self._config = None
        self._cmatrix = None
        self._user = None
        self._tool_user = None
        self._matrix = None
        self._matrix4tool = None
        folder = os.path.dirname(synthesis.filename)
        self.dir = abspath(f"{folder}/{name}")

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
        return list(scheme.keys())

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
            self._config = namedtuple("Config", "tool repack profile")(
                tool, repack, profile)
        return self._config

    def _used_by(self, tool=False, repack=False):
        graph = self._synthesis.holograph if tool else self._synthesis.graph
        result = set()
        for name in graph:
            if name == self.name:
                continue

            pkg = self._synthesis.package[name]
            if pkg.config.tool and not tool:
                continue
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
    def matrix(self):
        """compiler configuration matrix"""
        if self._cmatrix is None:
            self._cmatrix = []
            for profile in self.config.profile:
                for scheme in self.scheme or ['None']:
                    project = Project(profile, scheme, directory=f'{self.name}')
                    if not project.available:
                        continue
                    self._cmatrix.append(namedtuple("CMatrix", "profile scheme")(
                        profile, scheme))
        return self._cmatrix

    @property
    def matrix4tool(self):
        if self._matrix4tool is None:
            self._matrix4tool = []
            for name in self.tool_user:
                pkg = self._synthesis.package[name]
                if not pkg.config.tool:
                    continue
                for c in pkg.matrix:
                    config = 'static' if c.scheme == 'None' else config
                    c = self.find_matrix(c.profile, config)
                    if c:
                        self._matrix4tool += c
        return self._matrix4tool

    def match_matrix(self, profile, scheme=None, tool=False):
        P = re.compile(profile) if profile else None
        S = re.compile(scheme) if scheme else None
        matrix = []
        for c in self.matrix4tool if tool else self.matrix:
            if P is None or P.match(c.profile):
                if S is None or S.match(c.scheme):
                    matrix.append(c)
        return matrix

    def find_matrix(self, profile, scheme=None, tool=False):
        matrix = []
        for c in self.matrix4tool if tool else self.matrix:
            if profile is None or c.profile == profile:
                if scheme is None or scheme == c.scheme:
                    matrix.append(c)
        return matrix


    def c_matrix(self, profile, scheme=None, tool=False):
        matrix = {}
        for c in self.match_matrix(profile, scheme, tool=tool):
            if c.profile not in matrix:
                matrix[c.profile] = set()
            matrix[c.profile].add(c.scheme)
        S = []
        result = []
        for pr, schemes in matrix.items():
            for p, s in result:
                if s == schemes:
                    p.add(pr)
                    break
            else:
                result.append(({pr}, schemes))
        return result










#        def _matrix(pat):
#            if isinstance(pat, str):
#                pat = re.compile(pat)
#            matrix = package.matrix4tool if tool else package.matrix
#            profiles = {}
#            schemes = []
#            for pr, s in matrix.items():
#                if re.match(pat, pr):
#                    if s not in schemes:
#                        schemes.append(s)
#                    index = schemes.index(s)
#                    if index not in profiles:
#                        profiles[index] = set()
#                    profiles[index].add(pr)
#            return [(prs, schemes[i]) for i, prs in profiles.items()]
#        mat = {}
#        for i in [5, 6, 7, 8]:
#            for j in ['', '-x86', '-armv7', '-armv8']:
#                mat[f"gcc{i}"] = r'^gcc{}{}\w*$'.format(i,j)
#        for i in [100, 200]:
#            mat[f"himix{i}"] = r'^himix{}\w*$'.format(i)
#        for i in [300, 400]:
#            mat[f"hisiv{i}"] = r'^hisiv{}\w*$'.format(i)
#        for i in [2019]:
#            mat[f"vs{i}"] = r'^vs20\d\d\w*$'
#
#        matrix = {}
#        for profile, pattern in mat.items():
#            m = _matrix(pattern)
#            if m:
#                matrix[profile] = m
#        return matrix
#
#
#    @property
#    def matrix(self):
#        if self._matrix is None:
#            self._matrix = {}
#            for profile in self.config.profile:
#                for scheme in self.scheme or ['None']:
#                    project = Project(profile, scheme, directory=f'{self.name}')
#                    if not project.available:
#                        continue
#                    if profile not in self._matrix:
#                        self._matrix[profile] = set()
#                    self._matrix[profile].add(scheme)
#        return self._matrix
#
#    @property
#    def matrix4tool(self, name=None):
#        """ matrix for tool <name>
#        """
#        if self._matrix4tool is None:
#            self._matrix4tool = {}
#            for name in self.used_by(tool=True) or []:
#                pkg = self._synthesis.package[name]
#                for profile, schemes in pkg.matrix.items():
#                    if profile not in self._matrix4tool:
#                        self._matrix4tool[profile] = set()
#                    self._matrix4tool[profile].update(schemes)
#        return self._matrix4tool


class Config(object):
    def __init__(self, filename=None):
        filename = filename or f"{_DIR}/../../config.yml"
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

        return result


class Synthesis(object):

    def __init__(self, filename):
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
    manager = Synthesis(f"{_DIR}/../../config.yml")
    manager.dump()


if __name__ == '__main__':
    sys.exit(main())
