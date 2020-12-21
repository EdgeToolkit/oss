# 使用Gitlab 持续集成配置管理

本项目中包的构建在Gitlab-CI 持续集成中分为三个阶段(stage)构建(build)、测试(test)、 发布(publish)。构建过程中的文件通过Gitlab的Artifact进行缓存管理。

## 环境及部署

## Runner实例配置规划

### 功能类型概述

#### 构建器(builder)

构建器用对包进行编译并将相关的生成文件作为Gitlab的Artifacts以提供给后续阶段使用。目前构建器提供MSVC，GCC两种编译环境分别用于编译Windows与Linux系统软件。GCC只提供Docker执行器的Gitlab-runner，有配置文件中指定编译docker镜像。

构建器环境提供的工具

* epm/conan/python3

* windows环境将提供 Visual Studio 2019

* Linux docker环境镜像支持所有Profiles中的编译镜像

  |                | builder | Windows | MSVC | Linux | docker | `bundle` |
  | -------------- | ------- | ------- | ---- | ----- | ------ | -------- |
  | `VisualStudio` | Y       | Y       | Y    |       |        | *        |
  | `GCC`          | Y       |         |      | Y     | Y      | *        |
  |                |         |         |      |       |        |          |

  `bundle` 具体为oss.<bundle-name> bundle-name定义在bundle.yml中

  `VisualStudio` 行构建的标签组合，可用于编译Microsoft Visual Studio 的开发库和应用程序Conan包。目前安装了Visual Studio 2019。

  如: `builder` `Windows` `MSVC` `oss.base-devel` 用户构建base-devel bundle中的conan包。

  `GCC` 行构建的标签组合，可用于编译 Linux GCC工具链的的开发库和应用程序Conan包，具体的docker镜像由Gitlab-CI配置文件中具体指定。

  如: `builder` `Linux` `docker` `oss.base` 用户构建base bundle中的conan包。

  不同的bundle会提供相应依赖的conan 仓库用户构建是下载依赖conan包。

  |            | 依赖Conan仓库                        |      |
  | ---------- | ------------------------------------ | ---- |
  | base-devel |                                      |      |
  | base       | `base-devel`                         |      |
  | data       | `base` `base-devel`                  |      |
  | network    | `data` `base` `base-devel`           |      |
  | app-devel  | `network` `data` `base` `base-devel` |      |

  

#### 测试器(runner)

测试器用于对编译的包进行测试验证。目前平台支持Windows，Linux。通用Linux系统使用Docker，嵌入式Linux系统需对设备进行配置并支持SSH和mount。

标签

|                          | runner | Winodows | Linux | docker | `bundle` | `device` |      |
| ------------------------ | ------ | -------- | ----- | ------ | -------- | -------- | ---- |
| `Windows` win32/w64      | Y      | Y        |       |        | *        |          |      |
| `Linux` 通用             | Y      |          | Y     | Y      | *        |          |      |
| `device` 嵌入式linux系统 | Y      |          | Y     |        | *        | *        |      |





#### 发布器(publisher)





Runner功能类型: