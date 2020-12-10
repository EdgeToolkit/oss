import os
import yaml
import glob
import copy
import re
import networkx as nx
import subprocess
from jinja2 import PackageLoader,Environment, FileSystemLoader

_DIR = os.path.dirname(os.path.abspath(__file__))


def md5sum(fineName, block_size=64 * 1024):
  with open(fineName, 'rb') as f:
    md5 = hashlib.md5()
    while True:
      data = f.read(block_size)
      if not data:
        break
      md5.update(data)
    
    return md5.hexdigest()


def jinja_render(context, template_file, path=None):
    """Renders the specified template into the file.

    :param template_file: the path of template relative to templates
    :param path: the path to write the templated contents to
    :param context: the parameters to pass to the rendering engine
    """
    template_dir = os.path.normpath(f"{_DIR}/templates")
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template(template_file)
    
    content = template.render(context).strip()
    if path:
        path = os.path.abspath(path)
        directory = os.path.dirname(path)
        if not os.path.exists(directory):
            os.makedirs(directory)

        with open(path, "w") as f:
            f.write(content)
    return content


def graph_grade(graph):
    """ grade nodes in graph
    """
    n = 1
    def _grade(g, result):
        indeps = set()

        bottom = set()
        for name, deps in g.items():
            if not deps:
                bottom.add(name)
        if bottom:
            result.append(bottom)
            [g.pop(i) for i in bottom]
            for name, deps in g.items():
                for it in result:
                    deps -= it
        if not g:
            return result
        return _grade(g, result)
    group = {k: set(graph.neighbors(k)) for k in graph.nodes()}
    return _grade(group, [])


def bump_version(version, inc=1):
    P = r'(?P<version>\d+)(-(?P<fix>\d+))?'
    m = re.match(P, str(version))
    ver = m.group('version')
    fix = m.group('fix') 
    fix = int(fix or '0') + inc
    return f'{ver}-{fix}'

    
def update_versions(filename, versions):
    from ruamel.yaml import YAML
    yml = YAML()
    _changed = {}

    with open(filename) as f:
        metainfo = yml.load(f)

    def _setver(src, dst):
        if str(src) != str(dst):
            src = dst
            _changed[src] = [dst, type(src), type(dst)]
            return dst
        return src

    name = metainfo['name']
    if name in versions:
        metainfo['version'] = _setver(metainfo['version'], versions[name])

    deps = metainfo.get('dependencies') or {}
    for name, value in deps.items():
        if name not in versions:
            continue
        ver = versions[name]
        if isinstance(value, (str, int, float)):
            deps[name] = _setver(deps[name], ver)
        elif isinstance(value, dict):
            value['version'] = _setver(value['version'], ver)
        else:
            raise Exception('Unkown dependencies format')
    if _changed:
        with open(filename, 'w') as f:
            yml.dump(metainfo, f)



def _cast(a, c):
    if isinstance(a, list):
        return list(filter(lambda x: x in c, a))
    elif isinstance(a, dict):
        return {i:a[i] for i in c}
    elif isinstance(a, set):
        return c
    else:
        raise TypeError('Unssport <{}> '.format(type(a)))

def difference(a, b):
    assert type(a) == type(b)
    c = set(a).difference(set(b))
    return _cast(a, c)
    
def intersection(a, b):
    assert type(a) == type(b)
    c = set(a).intersection(set(b))
    return _cast(a, c)


def ancestor(nodes, graph):
    result = set()
    for name in graph.nodes:
        if name in nodes or name in result:
            continue
        for i in nodes:
            if nx.has_path(graph, name, i):
                result.add(name)
                break
    return result


def descendant(nodes, graph):
    result = set()
    for i in nodes:
        for name in graph.nodes:
            if name in nodes or name in result:
                continue
            if nx.has_path(graph, i, name):
                result.add(name)
                break
    return result


class epm_command(object):
    def __init__(self, profile, scheme=None, log_dir=None, dry_run=False):
        self._profile = profile
        self._scheme = scheme
        self._log_prefix = profile
        self._dry_run = dry_run
        self._command_prefix = ['epm', '-p', profile]
        if scheme:
            self._command += ['-s',  scheme]
            self._log_prefix += f'-{scheme}'
        self._file = None
        self._log_dir = log_dir

    def __enter__(self):
        if self._log_dir:
            from conans.tools import mkdir
            mkdir(self._log_dir)
            self._file = open(f"{self._log_dir}/{self._log_prefix}.log", 'w')
        return self
    
    def run(self, command, args=[], hint=None):
        command = self._command_prefix + [command] + args
        if self._dry_run:
            print(f"$", " ".join(command))
            return 0
        proc = subprocess.run(command, stdout=self._file, stderr=self._file)
        return proc.returncode
    
    def __exit__(self, exc_type, exc_value, traceback):
        if self._file:
            self._file.close()


class DepGraph(object):

    def __init__(self, graph):
        self._graph = graph
        self._topo = None
        self._layout = None

    @property
    def topo(self):
        if self._topo is None:
            self._topo = list(reversed(list(nx.topological_sort(self._graph))))
        return self._topo

    @property
    def layout(self):
        if self._layout is None:
            self._layout = self.layout_analyze(self._graph)
        return self._layout

    @staticmethod
    def layout_analyze(graph):
        """ grade nodes in graph
        """

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
        return _analyze(group, [])


class ObjectView(object):
    """Object view of a dict, updating the passed in dict when values are set
    or deleted. "ObjectView" the contents of a dict...: """

    def __init__(self, d):
        # since __setattr__ is overridden, self.__dict = d doesn't work
        object.__setattr__(self, '_ObjectView__dict', d)

    # Dictionary-like access / updates
    def __getitem__(self, name):
        value = self.__dict[name]
        if isinstance(value, dict):  # recursively view sub-dicts as objects
            value = ObjectView(value)
        elif isinstance(value, (list, tuple, set)):
            value = []
            for i in self.__dict[name]:
                if isinstance(i, dict):
                    value.append(ObjectView(i))
                else:
                    value.append(i)

        return value

    def __iter__(self):
        return iter(self._ObjectView__dict)

    def __setitem__(self, name, value):
        self.__dict[name] = value

    def __delitem__(self, name):
        del self.__dict[name]

    # Object-like access / updates
    def __getattr__(self, name):
        return self[name] if name in self else None

    def __setattr__(self, name, value):
        self[name] = value

    def __delattr__(self, name):
        del self[name]

    def __repr__(self):
        return "%s(%r)" % (type(self).__name__, self.__dict)

    def __str__(self):
        return str(self.__dict)




#################################
#    Test 
#################################
def test_graph():
    import pprint
    G=nx.DiGraph()
    G.add_nodes_from([1,2,3,4,5,6])
    G.add_edges_from([(4,1), (4,2),(4,3),  (5,2),(5,3),(6,4), (6,3)])
    #print('graph_stage\n', graph_stage(G))
    grade = graph_grade(G)
    print('++++++++++++++++++++++++++')
    pprint.pprint(grade)
    print(nx.flow_hierarchy(G))

def test_ObjectView():
    filename = os.path.expanduser("~/config/gitlab-ci/config.yml")
    with open(filename) as f:
        obj = ObjectView(yaml.safe_load(f))
    #print(obj)
    for i in obj.machine:
        print(i)
    print(type(obj))
    for i in obj.bundle:
        print("*", i.name, i.remote, i.x)

if __name__ == '__main__':
    test_ObjectView()
