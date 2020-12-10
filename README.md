# oss





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

