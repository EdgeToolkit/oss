#!/usr/bin/env python3
#from ansible.module_utils.basic import *
#import gitlab
#from oss_utils.gitlab_runner import GitlabRunner, GitlabRunnerDB, load_config
#
#module = AnsibleModule(
#    argument_spec = dict(
#        hostname=dict(required=True, type='str'),
#        type=dict(required=True, type='str'),
#        db=dict(required=True, type='str'),
#        config=dict(required=True, type='str')
#        ),
#)
#
#def register(param):
#    db = GitlabRunnerDB(param['db'])
#    config = load_config(param['config'])
#    gl = gitlab.Gitlab(config['gitlab']['url'], config['gitlab']['private_token'])
#    for workbench in config['workbench']:
#        gr = GitlabRunner(hostname=param['hostname'], type=param['type'], workbench=workbench,
#                          gitlab=gl, db=db)
#        gr.register(config['gitlab']['register_token'])
#    #return gr.register(param['register_token'])
#register(module.params)
#module.exit_json()

