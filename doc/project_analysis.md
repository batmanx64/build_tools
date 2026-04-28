# ONLYOFFICE DocumentServer 项目分析记录

## 1. 项目总结
ONLYOFFICE DocumentServer（现称 ONLYOFFICE Docs）是一个免费的在线协作办公套件，提供文本文档、电子表格、演示文稿、表单、PDF 和图表的查看器和编辑器。它完全兼容 Office Open XML 格式（.docx、.xlsx、.pptx），支持实时协作编辑。

该项目可以作为 ONLYOFFICE DocSpace 和 ONLYOFFICE Workspace 的一部分使用，或与第三方同步共享解决方案（如 Odoo、Moodle、Nextcloud 等）集成。

项目包含三个版本：Community Edition（社区版）、Enterprise Edition（企业版）和 Developer Edition（开发者版）。

## 2. 整体架构和技术栈

### 架构
项目采用多组件分布式架构，主要包括：

- **server**: 后端服务器软件层，是所有其他组件的基础
- **core**: 服务器核心组件，负责文档格式转换（DOC、DOCX、ODT、RTF、TXT、PDF、HTML、EPUB、XPS、DjVu、XLS、XLSX、ODS、CSV、PPT、PPTX、ODP）
- **sdkjs**: JavaScript SDK，包含所有客户端交互的 API
- **web-apps**: 前端界面，构建程序界面，允许用户创建、编辑、保存和导出文档
- **dictionaries**: 各种语言的字典，用于拼写检查
- **build_tools**: 构建工具，用于编译整个项目

### 技术栈
- **后端**: Node.js (server), C++ (core)
- **前端**: JavaScript (sdkjs, web-apps), HTML/CSS
- **构建工具**: Python (build scripts), Qt (desktop apps), Docker
- **数据库**: PostgreSQL (默认)
- **其他**: Git (版本控制), QMake (构建系统)

## 3. 核心入口文件和主要模块

### 核心入口文件
- `configure.py`: 配置脚本，处理构建参数和选项
- `make.py`: 主构建脚本，协调整个构建过程

### 主要模块 (build_tools/scripts/)
- `config.py`: 配置管理
- `base.py`: 基础工具函数
- `build_sln.py`: 解决方案构建（C++ 项目）
- `build_js.py`: JavaScript 构建
- `build_server.py`: 服务器构建
- `deploy.py`: 部署脚本
- `make_common.py`: 通用构建逻辑
- `develop/`: 开发相关脚本

## 4. 编译方式和必要参数

### 编译流程
1. 运行 `configure.py` 设置构建选项
2. 运行 `make.py` 执行构建
3. 可选：使用 `automate.py` (在 tools/linux/) 自动化构建

### 主要编译参数 (configure.py)

#### 基本参数
- `--update`: 是否更新/克隆仓库 (1=true, 0=false)
- `--branch`: 分支/标签名 (默认: master)
- `--clean`: 是否重新构建 (1=true)
- `--module`: 要构建的模块 (core, desktop, builder, server, mobile 等)

#### 平台参数
- `--platform`: 目标平台 (native, win_64, linux_64, mac_64, android 等)

#### 开发参数
- `--develop`: 开发模式 (0=false, 1=true)
- `--beta`: 测试版模式

#### 数据库参数
- `--sql-type`: 数据库类型 (默认: postgres)
- `--db-port`: 数据库端口 (默认: 5432)
- `--db-name`: 数据库名 (默认: onlyoffice)
- `--db-user`: 数据库用户 (默认: onlyoffice)
- `--db-pass`: 数据库密码 (默认: onlyoffice)

#### 其他参数
- `--qt-dir`: Qt 目录路径
- `--compiler`: 编译器名称
- `--branding`: 品牌定制路径
- `--multiprocess`: 多进程构建 (默认: 1)

### 示例命令
```bash
# 配置构建选项
python configure.py --update=1 --branch=master --module="core server sdkjs web-apps" --platform=linux_64

# 执行构建
python make.py
```

### Docker 构建
```bash
# 构建 Docker 镜像
docker build --tag onlyoffice-document-editors-builder .

# 运行容器构建
docker run -v $PWD/out:/build_tools/out onlyoffice-document-editors-builder
```

### 单独构建产品
```bash
# 仅构建 Document Builder
./automate.py builder

# 构建 Desktop Editors 和 Document Server
./automate.py desktop server
```

构建输出位于 `./out` 目录中。