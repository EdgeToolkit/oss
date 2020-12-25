#!/usr/bin/env python3
import os
import argparse
import subprocess


def main():
    parser = argparse.ArgumentParser(prog='EdgeToolkit auto deployment ansible-playbook wrapper.')
    subs = parser.add_subparsers(dest='cmd')
    def _global_options(subc):        
        subc.add_argument('-i', '--host', default='~/.edgetoolkit/config/hosts',help='config file path.')
        subc.add_argument('--verbose', default=0, type=int)

    # ======================================== #
    #   Gitlab
    # ======================================== #
    gitlab = subs.add_parser('gitlab', help='Gitlab deployment operation')
    _global_options(gitlab)
    gitlab.add_argument('--install', default=False, action='store_true', help="install Gitlab")
    gitlab.add_argument('--register-runner', default=False, action='store_true', help="register gitlab runner")
    gitlab.add_argument('--delete-runner', default=False, action='store_true', help="delete gitlab runner")
    gitlab.add_argument('--deploy-runner', default=False, action='store_true', help="deployment gitlab runner")
    
    args = parser.parse_args()
    WD = os.path.dirname(__file__)
    ansible = ['ansible-playbook', '-i', args.host]
    if args.verbose:
        ansible.append('-{}'.format("v"*args.verbose))
    os.environ['PYTHONPATH'] = os.path.join(WD, 'library','module_utils')

    if args.cmd == 'gitlab':
        if args.install:
            subprocess.run(ansible + ['gitlab.yml'], cwd=WD)
        if args.delete_runner:
            subprocess.run(ansible + ['gitlab-runner.yml', '-e', 'ACTION=delete'], cwd=WD)
            
        if args.register_runner:
            subprocess.run(ansible + ['gitlab-runner.yml', '-e', 'ACTION=register'], cwd=WD)
            
        if args.deploy_runner:
            subprocess.run(ansible + ['gitlab-runner.yml', '-e', 'ACTION=deploy'], cwd=WD)


if __name__ == '__main__':
    main()