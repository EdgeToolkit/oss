import sys
import os
import argparse

_DIR = os.path.dirname(__file__)
sys.path.insert(0, f"{_DIR}/../lib")
from ci import Gitlab


def gitlab_ci_generate(args):
    """generate gitlab ci config file
    """
    gitlab = Gitlab()
    return gitlab.generate(args)


def main():
    parser = argparse.ArgumentParser(prog='Open source software gitlab command tools')
    subs = parser.add_subparsers()

    # gitlab
    cmd = subs.add_parser('generate', help='Generate gitlab runner config')
    cmd.add_argument('--layout', default=None, help='Generate config for bundle')
    cmd.set_defaults(func=gitlab_ci_generate)

    args = parser.parse_args()
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
