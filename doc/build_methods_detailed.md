# ONLYOFFICE DocumentServer 构建方式详解

## 概述
ONLYOFFICE DocumentServer 支持三种主要的构建方式：开发环境构建、生产环境构建和 Docker 容器构建。每种方式都有特定的参数、配置和许可证要求。

## 许可证信息
- **主许可证**: GNU Affero General Public License (AGPL) v3
- **位置**: build_tools/LICENSE.txt
- **特点**: 专为网络服务器软件设计，确保修改后的源代码对社区可用
- **要求**: 网络服务器操作者必须向用户提供修改版本的源代码

## 1. 开发环境构建

### 适用场景
- 开发者本地开发和调试
- 需要频繁修改代码
- 不需要优化生产性能

### 主要参数
```bash
# configure.py 参数
--develop=1                    # 启用开发模式
--update=1                     # 更新仓库 (1=true, 0=false)
--update-light=1               # 轻量更新 (仅拉取，不切换分支)
--branch=<branch_name>         # 分支名 (默认: master)
--module=<modules>             # 要构建的模块
                               # 常用值: core, server, desktop, builder, mobile, osign
                               # JS 相关仓库: sdkjs, web-apps (用于 JS 构建/部署，但不是 sln.json 中的主构建模块)
--platform=<platform>          # 平台 (native, linux_64, win_64, mac_64 等)
--clean=0                      # 不重新构建 (开发模式通常设为0)
--multiprocess=1               # 启用多进程构建
```

### 构建流程
1. **配置阶段**:
   ```bash
   python configure.py --develop=1 --update=1 --module="server sdkjs web-apps" --platform=native
   ```

2. **构建阶段**:
   ```bash
   python make.py
   ```

> 开发模式下 `make.py` 会先执行 `develop.make()`，再进入 `build_sln.make()`、`build_js.make()`、`build_server.make()` 和 `deploy.make()` 阶段。
> `build_js.make()` 默认会构建 JS 资源，除非环境变量 `OO_NO_BUILD_JS=1` 被设置。

### 开发模式特点
- **增量构建**: 不清理之前的构建产物
- **源码映射**: 保留源码结构便于调试
- **热重载**: 支持代码修改后快速重启服务
- **调试信息**: 包含详细的调试日志和错误信息

### 模块名称与编译路径匹配说明
- `--module` 参数可指定多个模块，使用空格分隔。
- `build_tools/sln.json` 中主要识别的模块为: `core`, `builder`, `server`, `desktop`, `mobile`, `osign`。
- `sdkjs` 和 `web-apps` 在构建系统中通常作为 JS 仓库和资源目录参与 `build_js` 阶段，而不是 `sln.json` 里直接的主构建模块。
- 如果仅指定 `sdkjs web-apps`，`build_sln` 阶段不会把它们当作独立项目构建；建议同时包含 `server` / `builder` / `desktop` 等主模块，以确保最终部署路径正确。
- 输出路径必须与模块类型对应：核心 C++ /服务模块走 `out/<platform>/onlyoffice/`，JS 资源走 `out/js/`。
- 如发现构建模块与输出路径不匹配，可通过调整 `--module` 为正确的主模块组合，或手动检查 `build_tools/sln.json` 中的模块定义。

### 配置文件
- **主配置文件**: scripts/develop/develop.py
- **服务器配置**: scripts/develop/config_server.py
- **依赖检查**: scripts/develop/dependence.py

### 输出位置
- JS 构建产物: build_tools/out/js/<branding>/
  - builder: `build_tools/out/js/onlyoffice/builder`
  - desktop: `build_tools/out/js/onlyoffice/desktop`
  - mobile: `build_tools/out/js/onlyoffice/mobile`
- 服务器/产品部署输出: `build_tools/out/<platform>/onlyoffice/`
  - Document Server: `build_tools/out/linux_64/onlyoffice/documentserver/`
  - Desktop Editors: `build_tools/out/linux_64/onlyoffice/desktopeditors/`
  - Document Builder: `build_tools/out/linux_64/onlyoffice/documentbuilder/`
- 简化说明: `build_tools/out/` 是构建输出的根目录，具体子目录由平台和目标模块决定
- 开发服务器: 直接在源码目录运行，无需打包

## 2. 生产环境构建

### 适用场景
- 正式部署和发布
- 需要优化性能和安全性
- 生产服务器运行

### 主要参数
```bash
# configure.py 参数
--develop=0                    # 生产模式 (默认)
--update=1                     # 更新仓库
--branch=<branch_name>         # 分支名 (默认: master)
--module=<modules>             # 要构建的模块
--platform=<platform>          # 目标平台
--clean=1                      # 重新构建 (默认)
--multiprocess=1               # 多进程构建
--sql-type=postgres           # 数据库类型 (默认: postgres)
--db-port=5432                # 数据库端口
--db-name=onlyoffice          # 数据库名
--db-user=onlyoffice          # 数据库用户
--db-pass=onlyoffice          # 数据库密码
--qt-dir=<path>               # Qt 目录路径 (桌面版需要)
--compiler=<compiler>         # 编译器 (gcc, clang 等)
--branding=<path>             # 品牌定制路径
--features=<features>         # 功能特性配置
```

### 构建流程
1. **配置阶段**:
   ```bash
   python configure.py --update=1 --branch=master --module="core server sdkjs web-apps" --platform=linux_64 --sql-type=postgres
   ```

2. **构建阶段**:
   ```bash
   python make.py
   ```

### 生产模式特点
- **完全构建**: 清理所有之前的构建产物
- **优化编译**: 启用编译器优化 (-O2/-O3)
- **代码混淆**: 移除调试信息，减小体积
- **安全加固**: 启用安全编译选项
- **可执行文件**: 生成独立的可执行文件

### 配置文件
- **主配置文件**: scripts/config.py
- **构建配置**: scripts/make_common.py
- **部署配置**: scripts/deploy.py

### 输出位置
- 构建产物: build_tools/out/linux_64/onlyoffice/ 目录
- 可执行文件: 各服务生成独立二进制文件

## 3. Docker 容器构建

### 适用场景
- 容器化部署
- 跨平台一致性
- 简化部署流程

### 主要参数
```bash
# Dockerfile 环境变量
BRANCH=master                 # 构建分支
DEBIAN_FRONTEND=noninteractive # 非交互式安装

# configure.py 参数 (在 Dockerfile CMD 中)
--sysroot=1                   # 使用 sysroot (Ubuntu 16.04)
--clean=0                     # 不重新构建
--update-light=1              # 轻量更新
--branch=${BRANCH}           # 使用环境变量分支
--update=1                    # 更新仓库
--module="desktop server builder"  # 构建模块
--qt-dir=<qt_path>            # Qt 路径
```

### 构建流程
1. **构建 Docker 镜像**:
   ```bash
   docker build --tag onlyoffice-document-editors-builder .
   ```

2. **运行容器构建**:
   ```bash
   docker run -v $PWD/out:/build_tools/out onlyoffice-document-editors-builder
   ```

3. **指定分支构建**:
   ```bash
   docker build --build-arg BRANCH=develop --tag onlyoffice-builder-develop .
   ```

### Docker 特点
- **隔离环境**: 所有依赖都在容器内
- **可重现构建**: 相同的 Dockerfile 保证一致结果
- **跨平台**: 在任何支持 Docker 的系统上构建
- **依赖管理**: 自动安装系统依赖和开发工具

### 配置文件
- **Dockerfile**: build_tools/Dockerfile
- **依赖脚本**: tools/linux/deps.py
- **Python 安装**: tools/linux/python.sh
- **Qt 获取**: tools/linux/qt_binary_fetch.py

### 输出位置
- 容器内: /build_tools/out/
- 宿主机: 挂载的本地目录 (通过 -v 参数)

## 构建模块说明

### Core 模块
- **技术**: C++
- **功能**: 文档格式转换引擎
- **构建工具**: CMake, Make
- **依赖**: Boost, Qt, OpenSSL 等

### Server 模块
- **技术**: Node.js
- **功能**: 后端服务 (DocService, FileConverter, Metrics)
- **构建工具**: npm, pkg
- **输出**: 可执行二进制文件

### SDKJS 模块
- **技术**: JavaScript
- **功能**: 前端编辑器 SDK
- **构建工具**: Grunt, Webpack
- **输出**: 压缩的 JS/CSS 文件

### Web-Apps 模块
- **技术**: JavaScript, HTML, CSS
- **功能**: 前端用户界面
- **构建工具**: Grunt, Webpack
- **输出**: 静态 Web 文件

### Desktop 模块
- **技术**: C++, Qt
- **功能**: 桌面应用程序
- **构建工具**: QMake, Make
- **输出**: 平台特定可执行文件

### Builder 模块
- **技术**: C++
- **功能**: 文档构建服务
- **构建工具**: CMake, Make
- **输出**: 可执行二进制文件

## 常见构建问题解决

### 依赖问题
- 确保所有系统依赖已安装
- 检查 Python 版本 (推荐 3.x)
- 验证 Git 和 Git-LFS

### 网络问题
- 配置代理如果在企业网络中
- 确保 Git 仓库可访问
- 检查防火墙设置

### 磁盘空间
- 构建需要至少 10GB 可用空间
- 清理旧的构建产物定期

### 平台兼容性
- 使用正确的 --platform 参数
- 确保目标平台支持所有依赖
- 检查交叉编译工具链

## 许可证合规性检查

### 开发环境
- 自动检查依赖许可证
- 运行: `python scripts/license_checker/check.py`

### 生产构建
- 包含许可证文件在发布包中
- 生成依赖许可证清单
- 验证 AGPL 合规性

### Docker 构建
- 基础镜像许可证检查
- 依赖许可证验证
- 最终镜像许可证文档