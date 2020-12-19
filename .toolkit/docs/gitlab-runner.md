# 使用Gitlab 持续集成配置管理

本项目中包的构建在Gitlab-CI 持续集成中分为三个阶段(stage)构建(build)、测试(test)、 发布(publish)。构建过程中的文件通过Gitlab的Artifact进行缓存管理。

## 环境及部署

## Runner实例配置规划

### 功能类型概述

#### 构建器(builder)

构建器用对包进行编译并将相关的归档文件作为Gitlab的Artifacts以提供给后续阶段使用。目前构建器提供MSVC，GCC两种编译环境分别用于编译Windows与Linux系统软件。GCC只提供Docker执行器的Gitlab-runner，有配置文件中指定编译docker镜像。

构建器环境提供的工具

* epm/conan/python3

* windows环境将提供 Visual Studio 2019

* Linux docker环境镜像支持所有Profiles中的编译镜像

  |      |      |      |
  | ---- | ---- | ---- |
  |      |      |      |
  |      |      |      |
  |      |      |      |

  

* 不同的Bundle提供对应的Conan仓库用于下载依赖包



#### 测试器(runner)

#### 发布器(publisher)





Runner功能类型: