# Gitlab-runner 部署设计

针对OSS的持续集成，需配置4大类的gitlab-runner

* 配置生成器 - `ci-config-generator`

  配置器用根据 .gitlab-ci.yml 的配置生成相关Pipeline配置文件，并用户trigger下游pipeline。

* 构建器 - `builder`

  构建器用于编译生成相关库和应用程序，以用下一步测试和部署

  `Linux` `docker` `builder`

  `Windows` `MSVC` `builder`

* 测试运行器 - `runner`

  对应程序进行测试

  `Linux` `docker` `runner`

  `Windows` `runner`

  

* 发布器 - `publisher`

  将测试通过的包发布到Conan仓库。

  `publisher`



workbench=oss/<bundle>/<ver>

