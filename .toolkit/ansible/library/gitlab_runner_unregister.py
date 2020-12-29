#!/usr/bin/env python3

from ansible.module_utils.basic import AnsibleModule
<<<<<<< HEAD
from oss_utils.gitlab_runner import GitlabRunnerManager, HashTable
=======
from oss_utils.gitlab_runner import GitlabRunnerManager #noqa
>>>>>>> e475437314df87f08d8d5a19db470aa228b15b4d
def _unregister(param):
    from oss_utils.gitlab_runner import GitlabRunner, GitlabRunnerDB, load_config #noqa
    import gitlab
    db = HashTable(param['db'])
    config = load_config(param['config'])
    
    gl = gitlab.Gitlab(config['gitlab']['url'], config['gitlab']['private_token'])
    hostname=param['hostname']
    result = {'changed': False, 'runner': []}
    for workbench in config['workbench']:
        for type in param['type']:
            runner = GitlabRunner(hostname, type=type, workbench=workbench, gitlab=gl, db=db)
            r = runner.unregister()
            if r:
                result['changed'] = True
                result['runner'].append({'id': r.id, 'name': r.name})
    return result

def unregister(param):
    manager = GitlabRunnerManager(param['config'], param['db'])
    result = {'changed': False, 'runner': []}
    for type in param['type']:
        runners = manager.unregister(hostname=param['hostname'],  type=type)
        for runner in runners:
            result['runner'].append({'id': runner.id, 'name': runner.name})

    return result

def run_module():
    # define available arguments/parameters a user can pass to the module
    module_args = dict(
        hostname=dict(required=True, type='str'),
        type=dict(default=[], type='list'),
        db=dict(required=True, type='str'),
        config=dict(required=True, type='str'),
    )

    result = dict(
        changed=False,
        runner=[],
        msg=''
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    result = unregister(module.params)
    module.exit_json(**result)


def main():
    run_module()

if __name__ == '__main__':
    main()