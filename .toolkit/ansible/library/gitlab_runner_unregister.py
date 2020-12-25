#!/usr/bin/env python3

from ansible.module_utils.basic import AnsibleModule

def unregister(param):
    from oss_utils.gitlab_runner import GitlabRunner, GitlabRunnerDB, load_config #noqa
    import gitlab
    db = GitlabRunnerDB(param['db'])
    config = load_config(param['config'])
    gl = gitlab.Gitlab(config['gitlab']['url'], config['gitlab']['private_token'])
    
    runners = GitlabRunner.do_unregister(hostname=param['hostname'],  type=param['type'], gitlab=gl, db=db)
    result = {'changed': True if runners else False, 'runner': []}

    for id, name in runners:
        result['runner'] = {'id': id, 'name': name}
    return result

def run_module():
    # define available arguments/parameters a user can pass to the module
    module_args = dict(
        hostname=dict(required=True, type='str'),
        type=dict(default=None, type='str'),
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