```bash
cd .toolkit/ansible
sudo ./playbook command/install.yml -e target=artifactory
```



| 安装软件    | 命令                                                | 说明                                                         |
| ----------- | --------------------------------------------------- | ------------------------------------------------------------ |
| Artifactory | `sudo ./playbook install.yml -e target=artifactory` | Access http://{{artifactory_host}}:{{ARTIFACTORY_WEB_PORT}} to do config with default admin user=admin password=password |
|             |                                                     |                                                              |
|             |                                                     |                                                              |

