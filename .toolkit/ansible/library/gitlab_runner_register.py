#!/usr/bin/env python3
from ansible.module_utils.basic import AnsibleModule

import gitlab
from oss_utils.gitlab_runner import GitlabRunnerManager #noqa

def register(param):
    manager = GitlabRunnerManager(param['config'], param['db'])
    result = []
    runners = manager.register(hostname=param['hostname'],  type=param['type'], platform=param['platform'])
    for runner in runners:
        result.append({'id': runner.id})

    return result


def run_module():
    module_args = dict(
        hostname=dict(required=True, type='str'),
        type=dict(required=True, type='str'),
        platform=dict(required=True, type='str'),
        db=dict(required=True, type='str'),
        config=dict(required=True, type='str'),
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

    result['runner'] = register(module.params)
    module.exit_json(**result)


def main():
    run_module()

if __name__ == '__main__':
    main()