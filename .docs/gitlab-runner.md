



## 标签规划



System: Windows Linux macOS

Arch:  x86_64,  armv7,  armv8

Kind: builder, runner,  deployer

simulator= iOS, Android



编译( with tag `builder`)

| 编译目标\标签 | `Windows`                | `Linux`                              | `Darwin`                 |
| ------------- | ------------------------ | ------------------------------------ | ------------------------ |
| Windows       | VS2019:   `x86` `x86_64` |                                      |                          |
| Linux         |                          | GCC:  `x86` `x86_64` `armv7` `armv8` |                          |
| Darwin        |                          |                                      | clang: `x86_64`          |
| iOS           |                          |                                      | clang: `x86_64`  `armv8` |
| Android       |                          | clang: `x86_64`  `armv8`             |                          |



运行器