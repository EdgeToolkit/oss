#!/bin/bash
__dirname=$(cd $(dirname ${BASH_SOURCE[0]} ) && pwd)
cd $__dirname/ansible
ansible-playbook  -i ~/.edgetoolkit/config/hosts -e 'ansible_python_interpreter=/usr/bin/python3'  $*
