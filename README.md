# oss

| package| version | ref-ver | status |
| :----: |

Generate bundle workbench config files, if not sepcified bundle name, all bundle will be generated.
You must insure ~/config/gitlab-ci/config.yml exist or use --config to set your path.
```sh
cd oss
pip install networkx
python .toolkit/script/bundle.py workbench toolset dev
```
```yaml
name: OSS
version: 1



bundle:
  - name: toolset
    remote: http://<IP>/artifactory/api/conan/OSS.toolset

  - name: base
    remote: http://<IP>/artifactory/api/conan/OSS.base

  - name: microservice
    remote: http://172.16.0.119:8060/artifactory/api/conan/OSS.microservice
    

tags:
  Windows:
    builder:
    - Windows
    - MSVC
    - builder
    runner:
    - Windows
    - runner
  Linux:
    deployer:
    - conan
    - deployer
    runner:
    - Linux
    - docker
    - runner
    builder:
    - Windows
    - MSVC
    - builder

gitlab:
  url: http://<HOSTNAME>
  token: g9fSbEEaqxJ57bZzkcNs

environment:
  EPM_MIRROR_MSYS2: http://<HOSTNAME>/mirrors/msys2

conan:
  username: XXXXX
  password: xxxxxxx

```

## GitLab-CI



## build all tools in Gitlab CI 

Open web brower and create new pipline with http://172.16.0.121:8000/epmkit/oss/-/pipelines/new# . 

![run-pipeline-via-web](.\docs\image\run-pipeline-via-web.png)

```

```

You should set the Variable `TARGET` as your requirement.

| Value     | Comments                                                     |      |
| --------- | ------------------------------------------------------------ | ---- |
| bootstrap | build all tools, except the redist package.                  |      |
| base      | build all base bundle package (not build tool)               |      |
| ${name}   | if you set the name of non-build package, only specified package to build. |      |

