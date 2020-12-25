#!/usr/bin/env python3

from ansible.module_utils.basic import AnsibleModule
#
#module = AnsibleModule(
#    argument_spec = dict(
#        hostname=dict(required=True, type='str'),
#        type=dict(default=None, type='str'),
#        #workbench=dict(default=None, type='str'),
#        #url=dict(required=True, type='str'),
#        #register_token=dict(required=True, type='str'),
#        #private_token=dict(required=True, type='str'),
#        db=dict(required=True, type='str'),
#        config=dict(required=True, type='str'),
#        ),
#)
#
#def unregister(param):
#    
#    db = GitlabRunnerDB(param['db'])
#    config = load_config(param['config'])
#    gl = gitlab.Gitlab(config['gitlab']['url'], config['gitlab']['private_token'])
#    return GitlabRunner.unregister(hostname=param['hostname'],  type=param['type'], gitlab=gl, db=db)
#result  = unregister(module.params)
#module.exit_json()



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

    # seed the result dict in the object
    # we primarily care about changed and state
    # changed is if this module effectively modified the target
    # state will include any data that you want your module to pass back
    # for consumption, for example, in a subsequent task
    result = dict(
        changed=False,
        runner=[],
        msg=''
    )

    # the AnsibleModule object will be our abstraction working with Ansible
    # this includes instantiation, a couple of common attr would be the
    # args/params passed to the execution, as well as if the module
    # supports check mode
    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    # if the user is working with this module in only check mode we do not
    # want to make any changes to the environment, just return the current
    # state with no modifications
    #if module.check_mode:
    #    module.exit_json(**result)
    #    return
    print('===============================================================================2')
    result = unregister(module.params)
    module.exit_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()