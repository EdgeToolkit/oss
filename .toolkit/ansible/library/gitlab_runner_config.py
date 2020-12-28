#!/usr/bin/env python3
from ansible.module_utils.basic import AnsibleModule

import gitlab
from oss_utils.gitlab_runner import GitlabRunnerManager #noqa

def generate_config(param):
    manager = GitlabRunnerManager(param['config'], param['db'])
    result = []
    runners = manager.generate(hostname=param['hostname'],  type=param['type'], platform=param['platform'], 
        home=param['home'], out_dir=param['out'])

    return result


def run_module():
    module_args = dict(
        hostname=dict(required=True, type='str'),
        type=dict(required=True, type='list'),
        platform=dict(required=True, type='str'),
        home=dict(required=True, type='str'),
        db=dict(required=True, type='str'),
        config=dict(required=True, type='str'),
        out=dict(required=True, type='str'),
    )

    result = dict(
        changed=False,
        runner=[],
    )    

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    if module.check_mode:
        module.exit_json(**result)

    result['runner'] = generate_config(module.params)
    module.exit_json(**result)


def main():
    run_module()

if __name__ == '__main__':
    main()