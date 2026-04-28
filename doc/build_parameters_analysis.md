# ONLYOFFICE Build Tools 编译参数完整分析

## 一、整体编译架构

编译系统的入口有两个核心脚本：

| 脚本 | 功能 |
|------|------|
| `configure.py` | 配置构建参数，将选项写入 `config` 文件 |
| `make.py` | 读取 `config` 文件，按阶段执行完整构建流程 |

`make.py` 的构建阶段顺序：
1. `develop.make()` — 开发模式（仅 --develop=1 时执行）
2. `build_js.make()` — 检查 OO_ONLY_BUILD_JS 环境变量（仅构建 JS 时用）
3. `make_common.make()` — 编译 Core 第三方依赖
4. `build_sln.make()` — 编译 C++ 项目（通过 qmake → make）
5. `build_js.make()` — 编译 JavaScript（sdkjs / web-apps）
6. `build_server.make()` — 打包 server 为可执行文件
7. `deploy.make()` — 部署产物到 out/ 目录

---

## 二、开发环境编译

### 2.1 触发方式

```bash
python configure.py --develop=1 [其他参数...]
python make.py
```

核心标识：`--develop=1`

### 2.2 完整参数列表

#### 基础参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--develop` | `0` | **必须设为 1** 启用开发模式 |
| `--update` | `1` | 是否更新/克隆仓库 (1=true, 0=false) |
| `--update-light` | `""` | 轻量更新，只拉取不切换分支（需 update=1） |
| `--branch` | `master` | 分支/标签名 |
| `--module` | `builder` | 构建模块（空格分隔），见下方模块说明 |
| `--platform` | `native` | 目标平台，开发时通常用 native |
| `--clean` | `1` | 开发时建议设为 0（增量构建） |

#### 数据库参数（开发时会自动检查并安装依赖）

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--sql-type` | `postgres` | 数据库类型 |
| `--db-port` | `5432` | 数据库端口 |
| `--db-name` | `onlyoffice` | 数据库名 |
| `--db-user` | `onlyoffice` | 数据库用户 |
| `--db-pass` | `onlyoffice` | 数据库密码 |

#### 路径参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--qt-dir` | `""` | Qt 目录（qmake 在 qt-dir/compiler/bin 下） |
| `--external-folder` | `""` | 外部文件夹路径（用于 sdkjs/web-apps 外部源码） |
| `--siteUrl` | `127.0.0.1` | 站点 URL |

#### 插件参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--sdkjs-plugin` | `default` | SDKJS 插件列表 |
| `--sdkjs-plugin-server` | `default` | Server 端插件列表 |
| `--sdkjs-addon` | `""` | SDKJS 插件列表 |
| `--server-addon` | `""` | Server 插件列表 |
| `--web-apps-addon` | `""` | Web-Apps 插件列表 |

#### 其他

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--branding` | `""` | 品牌定制路径 |
| `--branding-name` | `""` | 品牌名称 |
| `--branding-url` | `""` | 品牌仓库 URL |
| `--git-protocol` | `auto` | Git 协议 (https, ssh, auto) |
| `--multiprocess` | `1` | 是否多进程编译 |
| `--beta` | `0` | 测试版模式 |

### 2.3 开发环境示例

```bash
# 最小开发环境（仅 server + JS 资源）
python configure.py --develop=1 --update=1 --module="server sdkjs web-apps" --platform=native --clean=0

# 带桌面编辑器
python configure.py --develop=1 --update=1 --module="desktop" --platform=native \
    --qt-dir="$(pwd)/tools/linux/qt_build/Qt-5.9.9" --clean=0

# 带 sysroot（跨平台 Linux arm64 开发）
python configure.py --develop=1 --update=1 --branch=develop --module="server sdkjs web-apps" \
    --platform=native --sysroot=1 --clean=0
```

### 2.4 开发模式构建行为

当 `develop=1` 时，`make.py` 执行 `develop.make()` 后直接 `exit(0)`，不执行后续的 C++ 编译、生产部署等阶段。

`develop.make()` 内部流程：

1. **依赖检查** (`dependence.check_dependencies()`)
   - 检查并自动安装缺失依赖：Git、Curl、Node.js、npm、7z、Java、Erlang、RabbitMQ、Grunt-CLI、PostgreSQL
   - 检查 PostgreSQL 配置（用户、数据库、密码、表结构）
   - 有 server-lockstorage 插件时额外检查 Redis

2. **构建开发版 Server** (`build_develop_server()`)
   - `build_server_with_addons()`: 对 server 和各 addon 执行 `npm ci` + `npm run build`
   - `build_js_develop()`: 开发版 JS 构建
     - SDKJS: `npm ci` → `grunt develop`（`WHITESPACE_ONLY` 级别，保留格式）
     - Web-Apps: `npm ci` → `grunt` + 翻译合并 + framework7-react 部署
     - **不进行** JS 代码压缩和混淆
   - `config_server.make()`:
     - 从 S3 (`repo-doc-onlyoffice-com.s3.amazonaws.com`) 下载预编译的 core 二进制文件（不解压源码编译 C++）
     - 解压到 `server/FileConverter/bin/`
     - 生成 `DoctRenderer.config` 配置文件
     - 下载 SDKJS 插件（v1）
     - 生成字体数据和演示文稿主题
     - 自动生成 `local-development-linux.json` 服务器配置

3. **JS 构建参数差异**

| 行为 | 开发模式 | 生产模式 |
|------|---------|---------|
| NODE_ENV | 不设置 | `production` |
| Closure Compiler 级别 | `WHITESPACE_ONLY` | `ADVANCED` |
| 代码格式化 | `PRETTY_PRINT` | 无（压缩） |
| beta 标识 | false | 取决于 --beta 参数 |
| PRODUCT_VERSION | 追加 "d" 后缀 | 原始版本号 |

### 2.5 开发模式输出

- **Server 运行目录**：直接在源码目录运行，不生成独立二进制
  ```bash
  cd out/linux_64/onlyoffice/documentserver/server/FileConverter
  LD_LIBRARY_PATH=$PWD/bin NODE_ENV=development-linux NODE_CONFIG_DIR=$PWD/../Common/config ./converter
  ```
- **JS 资源**：`out/js/<branding>/`

### 2.6 开发模式运行命令

```bash
# FileConverter 服务
cd out/linux_64/onlyoffice/documentserver/server/FileConverter
LD_LIBRARY_PATH=$PWD/bin NODE_ENV=development-linux NODE_CONFIG_DIR=$PWD/../Common/config ./converter

# DocService 服务
cd out/linux_64/onlyoffice/documentserver/server/DocService
NODE_ENV=development-linux NODE_CONFIG_DIR=$PWD/../Common/config ./docservice
```

---

## 三、生产环境编译

### 3.1 触发方式

```bash
python configure.py --develop=0 [其他参数...]
python make.py
```

`--develop=0` 是默认值，可省略。关键：**不加** `--develop=1` 即为生产编译。

### 3.2 完整参数列表

#### 基础参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--develop` | `0` | 生产模式（默认，可省略） |
| `--update` | `1` | 是否更新/克隆仓库 |
| `--update-light` | `""` | 轻量更新 |
| `--branch` | `master` | 分支/标签名 |
| `--module` | `builder` | 构建模块 |
| `--clean` | `1` | 完全重新构建（建议保持默认） |
| `--beta` | `0` | 测试版模式 |

#### 平台参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--platform` | `native` | 目标平台，支持的值： |
| | | `win_64`, `win_32`, `win_64_xp`, `win_32_xp`, `win_arm64` |
| | | `linux_64`, `linux_32`, `linux_arm64` |
| | | `mac_64`, `mac_arm64` |
| | | `ios` |
| | | `android_arm64_v8a`, `android_armv7`, `android_x86`, `android_x86_64` |
| | | 组合值：`native`, `all`, `windows`, `linux`, `mac`, `android` |
| `--sysroot` | `0` | Linux 专用：使用 Ubuntu 16.04 sysroot 编译 C++。设为 `1` 自动下载，也可指定自定义路径 |
| `--qemu-win-arm64-dir` | `""` | QEMU 虚拟机目录（用于 win_arm64 交叉编译） |

#### 编译器参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--compiler` | 自动检测 | 编译器名：`msvc2015`, `msvc2015_64`, `gcc`, `gcc_64`, `clang`, `clang_64` 等 |
| `--vs-version` | `2015` | Visual Studio 版本（Windows） |
| `--vs-path` | 自动检测 | vcvarsall 路径（Windows） |
| `--qt-dir` | `""` | Qt 目录路径 |
| `--qt-dir-xp` | `""` | Windows XP 专用 Qt 目录 |
| `--no-apps` | `0` | 设为 `1` 禁用使用 Qt 的桌面应用构建 |

#### 数据库参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--sql-type` | `postgres` | 数据库类型 |
| `--db-port` | `5432` | 数据库端口 |
| `--db-name` | `onlyoffice` | 数据库名 |
| `--db-user` | `onlyoffice` | 数据库用户 |
| `--db-pass` | `onlyoffice` | 数据库密码 |

#### 模块与配置

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--config` | `""` | 额外的 qmake 配置参数（空格分隔）。关键值： |
| | | `debug` — Debug 构建 |
| | | `release` — Release 构建 |
| | | `updmodule` — 构建 Windows 桌面更新模块 |
| | | `core_disable_all_warnings` — 禁用所有警告（默认开启） |
| | | `core_enable_all_warnings` — 启用所有警告 |
| | | `use_v8` — 使用 V8 JS 引擎（而非 JavaScriptCore） |
| | | `bundle_dylibs` — macOS 上打包 .framework |
| | | `bundle_xcframeworks` — iOS 上创建 xcframework |
| | | `cef_version_107` — 使用 CEF 107（旧 GCC 环境自动启用） |
| | | `v8_version_60` — 使用 V8 v6.0（旧编译环境自动启用） |
| `--features` | `""` | 原生特性配置（config addon） |
| `--themesparams` | `""` | 演示文稿主题缩略图生成参数 |

#### 品牌定制

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--branding` | `""` | 品牌定制路径 |
| `--branding-name` | `""` | 品牌名称 |
| `--branding-url` | `""` | 品牌仓库 URL |

#### Addon/插件参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--sdkjs-addon` | `[]` | SDKJS addon（可多次指定） |
| `--sdkjs-addon-desktop` | `[]` | 桌面端 SDKJS addon（可多次指定） |
| `--server-addon` | `[]` | Server addon（可多次指定） |
| `--web-apps-addon` | `[]` | Web-Apps addon（可多次指定） |
| `--sdkjs-plugin` | `default` | 全部插件列表 |
| `--sdkjs-plugin-server` | `default` | Server 端插件列表 |

#### 其他

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--git-protocol` | `auto` | Git 协议 (https / ssh / auto) |
| `--multiprocess` | `1` | 多进程 make (-jN) |
| `--siteUrl` | `127.0.0.1` | 站点 URL |
| `--external-folder` | `""` | 外部文件夹路径 |
| `--use-system-qt` | 不设置 | 设为 1 使用系统 Qt |

### 3.3 生产环境构建流程

`make.py` 在生产模式下按以下顺序执行（`develop=0`，`develop.make()` 直接返回）：

```
make_common.make()  →  编译 Core 第三方依赖（boost, icu, v8, openssl, hunspell 等）
build_sln.make()    →  qmake 生成 Makefile → make 编译 C++ 项目
build_js.make()     →  npm install → grunt（ADVANCED 级别压缩）
build_server.make() →  npm ci → npm run build → pkg 打包为独立二进制
deploy.make()       →  复制产物到 out/ 目录
```

各阶段详细信息：

#### 阶段 1: make_common — Core 第三方库编译
- `scripts/core_common/make_common.py`
- 编译模块包括：boost, icu, v8/v8_89, openssl, hunspell, hyphen, cef, socket_io, glew, libvlc, html2, iwork, googletest 等
- 平台相关：Android 额外编译 openssl_mobile, socketrocket, ixwebsocket

#### 阶段 2: build_sln — C++ 项目编译
- 读取 `sln.json` 中定义的模块和项目列表
- 根据 `--module` 参数筛选要编译的子项目
- 支持条件编译过滤（按平台、配置选项）
- `qmake.make()` 流程：
  1. 检测 Qt 环境，确认目标平台受支持
  2. 执行 `qmake -nocache <project.pro> CONFIG+=<config>` 生成 Makefile
  3. 执行 `make -f Makefile.<platform>` 编译
- 支持 sysroot 交叉编译（Linux arm64 等）
- Windows 上通过 vcvarsall.bat 设置 VS 编译环境

#### 阶段 3: build_js — JavaScript 编译
- `scripts/build_js.py`
- 设置 `NODE_ENV=production`
- SDKJS builder: `grunt --level=ADVANCED --beta=<true/false>`
- SDKJS desktop: `grunt --level=ADVANCED --desktop=true`
- Web-Apps: `grunt --force --verbose`
- SDKJS native (mobile): `grunt --level=ADVANCED --mobile=true`

#### 阶段 4: build_server — 服务器打包
- `scripts/build_server.py`
- 替换版本号到源文件（buildNumber, buildVersion, buildDate）
- 使用 `pkg` 将 Node.js 服务打包为独立二进制：
  - `DocService` → `docservice`
  - `FileConverter` → `converter`
  - `Metrics` → `metrics`
  - `AdminPanel`（可选）→ `adminpanel`
  - `Example` → `example`
- 目标平台格式：`node20-<os>[-<arch>]`（如 `node20-linux`, `node20-linux-arm64`, `node20-win`）
- 内存选项：`max_old_space_size=6144`（6GB）

#### 阶段 5: deploy — 部署
- `scripts/deploy.py`
- 根据模块类型调用对应的 deploy 脚本：
  - `deploy_desktop.make()` — 桌面编辑器部署
  - `deploy_builder.make()` — 文档构建器部署
  - `deploy_server.make()` — Server 部署
  - `deploy_core.make()` — Core 部署
  - `deploy_mobile.make()` — 移动端部署
- 产物复制到 `out/<platform>/onlyoffice/` 目录

### 3.4 生产环境示例

```bash
# 完整生产构建（server + builder + desktop）
python configure.py \
    --update=1 \
    --branch=master \
    --module="desktop server builder" \
    --platform=linux_64 \
    --clean=1 \
    --multiprocess=1 \
    --qt-dir="$(pwd)/tools/linux/qt_build/Qt-5.9.9"

python make.py

# 仅构建 server
python configure.py --module="server sdkjs web-apps" --platform=linux_64
python make.py

# Windows 构建
python configure.py --module="desktop server builder" --platform=win_64 \
    --vs-version=2019
python make.py

# macOS 构建
python configure.py --module="desktop server builder" --platform=mac_64 \
    --qt-dir="<qt_path>"
python make.py

# 使用 sysroot 的 Linux 构建（支持旧系统兼容）
python configure.py --module="desktop server builder" --platform=linux_64 --sysroot=1 \
    --qt-dir="$(pwd)/tools/linux/qt_build/Qt-5.9.9"
python make.py

# Debug 构建
python configure.py --module="server sdkjs web-apps" --platform=linux_64 --config="debug"
python make.py
```

### 3.5 生产环境输出

```
out/
├── <platform>/              # 如 linux_64, win_64, mac_64
│   └── onlyoffice/
│       ├── documentserver/  # Document Server
│       │   ├── server/
│       │   │   ├── FileConverter/
│       │   │   │   └── converter      # 独立二进制
│       │   │   ├── DocService/
│       │   │   │   └── docservice     # 独立二进制
│       │   │   └── Metrics/
│       │   │       └── metrics        # 独立二进制
│       │   └── ...
│       ├── desktopeditors/  # Desktop Editors
│       └── documentbuilder/ # Document Builder
└── js/                      # JS 构建产物
    └── <branding>/
        ├── builder/
        ├── desktop/
        └── mobile/
```

---

## 四、开发环境 vs 生产环境 对比总览

| 维度 | 开发环境 (`--develop=1`) | 生产环境 (`--develop=0`) |
|------|--------------------------|--------------------------|
| **C++ Core 编译** | 不编译，下载预编译二进制 | 从源码完整编译 |
| **JS 压缩级别** | `WHITESPACE_ONLY`（保留格式可读） | `ADVANCED`（完全压缩混淆） |
| **NODE_ENV** | 不设置 | `production` |
| **Server 打包** | 不打包，直接运行 Node.js | `pkg` 打包为独立二进制 |
| **依赖处理** | 自动检查并安装系统依赖 | 需手动确保依赖就绪 |
| **清理构建** | 建议 `--clean=0`（增量） | 默认 `--clean=1`（完全清理） |
| **版本号** | 追加 "d" 后缀 | 使用原始版本号 |
| **构建耗时** | 较快（分钟级） | 慢（小时级，需编译 C++） |
| **调试体验** | 源码可读，支持直接调试 | 代码压缩混淆，难调试 |
| **可移植性** | 依赖本地环境 | 独立可执行文件，可分发 |
| **适用场景** | 本地开发、调试、修改代码 | 发布、部署、CI/CD |

---

## 五、模块 (--module) 说明

| 模块名 | 类别 | 说明 | 包含子项目 |
|--------|------|------|-----------|
| `core` | C++ | 核心文档格式转换引擎 | kernel, graphics, PdfFile, XpsFile, DjVuFile, OFDFile, HtmlFile2, Fb2File, EpubFile, HwpFile, X2tConverter, DocxRenderer, doctrenderer, AllFontsGen, allthemesgen, hunspell 等 |
| `builder` | C++ | 文档构建器 | core + docbuilder.pro + docbuilder Java/Python wrapper |
| `server` | C++/Node.js | 文档服务器 | core (C++ 部分) + Node.js 打包（pkg） |
| `desktop` | C++ | 桌面编辑器 | core + multimedia + desktop-sdk + desktop-apps |
| `mobile` | C++ | 移动端编辑器 | core |
| `osign` | C++ | Office 签名库 | xmlsec 签名支持 |
| `sdkjs` | JS 仓库 | JavaScript SDK | JS 构建资源（参与 build_js 阶段） |
| `web-apps` | JS 仓库 | 前端 UI | JS 构建资源（参与 build_js 阶段） |

> 注意：`sdkjs` 和 `web-apps` 用于控制仓库克隆和 JS 资源构建，而非 `sln.json` 中的 C++ 编译模块。

---

## 六、平台 (--platform) 完整列表

| 平台值 | 说明 | 编译器 |
|--------|------|--------|
| `native` | 自动检测当前系统 | 自动 |
| `win_64` | Windows 64-bit | msvc2019_64 |
| `win_32` | Windows 32-bit | msvc2019 |
| `win_64_xp` | Windows XP 64-bit | msvc2015_64 |
| `win_32_xp` | Windows XP 32-bit | msvc2015 |
| `win_arm64` | Windows ARM64 | msvc2019_arm64 |
| `linux_64` | Linux 64-bit | gcc_64 |
| `linux_32` | Linux 32-bit | gcc |
| `linux_arm64` | Linux ARM64 | gcc_arm64 |
| `mac_64` | macOS Intel 64-bit | clang_64 |
| `mac_arm64` | macOS Apple Silicon | clang_64 (+ apple_silicon) |
| `ios` | iOS | ios |
| `android_arm64_v8a` | Android ARM64 | android_arm64_v8a |
| `android_armv7` | Android ARMv7 | android_armv7 |
| `android_x86` | Android x86 | android_x86 |
| `android_x86_64` | Android x86_64 | android_x86_64 |

组合值：
| 组合值 | 展开为 |
|--------|--------|
| `all` | 当前系统的所有变体 |
| `windows` | win_64 win_32 win_64_xp win_32_xp |
| `linux` | linux_64 linux_32 |
| `mac` | mac_64 |

---

## 七、config 文件

`configure.py` 将参数写入 `build_tools/config` 文件，`make.py` 通过 `config.parse()` 读取。可手动编辑此文件绕过 `configure.py`。格式示例：

```
update="1"
branch="master"
clean="1"
module="server sdkjs web-apps"
develop="0"
beta="0"
platform="linux_64"
sql-type="postgres"
db-port="5432"
db-name="onlyoffice"
db-user="onlyoffice"
db-pass="onlyoffice"
```

---

## 八、环境变量

| 变量 | 说明 |
|------|------|
| `PRODUCT_VERSION` | 产品版本号（从 version 文件读取，如 9.3.1） |
| `BUILD_NUMBER` | 构建号（默认 0） |
| `BUILD_PLATFORM` | 当前构建平台 |
| `OO_RUNNING_BRANDING` | 是否正在运行品牌构建 |
| `OO_BRANDING` | 品牌名称 |
| `OO_ONLY_BUILD_JS` | 设为 1 仅构建 JS（跳过 C++ 编译） |
| `OO_NO_BUILD_JS` | 设为 1 跳过 JS 构建 |
| `OO_BUILD_ONLY_BRANDING` | 仅构建品牌资源 |
| `NODE_ENV` | 生产模式设为 `production`（JS 构建时） |
| `QT_DEPLOY` | Qt 部署目录 |
| `OS_DEPLOY` | 当前构建的 OS 平台 |

---

## 九、Docker 构建

Dockerfile 使用的是**生产环境参数**：

```dockerfile
CMD ["sh", "-c", "./tools/linux/python3/bin/python3 ./configure.py \
    --sysroot \"1\" \
    --clean \"0\" \
    --update-light \"1\" \
    --branch \"${BRANCH}\" \
    --update \"1\" \
    --module \"desktop server builder\" \
    --qt-dir \"$(pwd)/tools/linux/qt_build/Qt-5.9.9\" \
    && ./tools/linux/python3/bin/python3 ./make.py"]
```

关键点：
- `--sysroot=1` — 使用 Ubuntu 16.04 sysroot（兼容旧系统）
- `--clean=0` — 容器内增量构建（每次 docker run 是新容器）
- `--update-light=1` — 快速更新（不切换分支，避免冲突）
- `--module="desktop server builder"` — 构建全部三个产品
