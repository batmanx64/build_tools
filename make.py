#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
make.py - ONLYOFFICE 构建系统的主构建脚本
==========================================
功能：读取 configure.py 生成的 config 文件，按顺序执行完整的构建流程。

构建阶段顺序：
  1. config.parse()            - 解析配置文件
  2. develop.make()            - 开发模式（仅 --develop=1 时执行）
  3. build_js.make()           - 检查 OO_ONLY_BUILD_JS（仅构建 JS 模式）
  4. make_common.make()        - 编译 Core 第三方依赖库
  5. build_sln.make()          - 编译 C++ 项目（qmake→make）
  6. build_js.make()           - 编译 JavaScript 资源（sdkjs/web-apps）
  7. build_server.make()       - 打包 Server 为独立可执行文件
  8. deploy.make()             - 部署所有产物到 out/ 目录

典型用法:
    python configure.py --module="server sdkjs web-apps" --platform=linux_64
    python make.py
"""

import os
import sys
# 添加脚本搜索路径，使得各子目录的模块可以被 import
__dir__name__ = os.path.dirname(os.path.abspath(__file__))
sys.path.append(__dir__name__ + '/scripts')
sys.path.append(__dir__name__ + '/scripts/develop')
sys.path.append(__dir__name__ + '/scripts/develop/vendor')
sys.path.append(__dir__name__ + '/scripts/core_common')
sys.path.append(__dir__name__ + '/scripts/core_common/modules')
sys.path.append(__dir__name__ + '/scripts/core_common/modules/android')
import config
import base
import build_sln
import build_js
import build_server
import deploy
import make_common
import develop
import argparse

# 解析额外参数（目前仅支持 --build-only-branding）
parser = argparse.ArgumentParser(description="options")
parser.add_argument("--build-only-branding", action="store_true")
args = parser.parse_args()

# 如果指定了仅构建品牌资源，设置环境变量后继续流程
if (args.build_only_branding):
  base.set_env("OO_BUILD_ONLY_BRANDING", "1")

# ---- 第 1 步：解析配置 ----
# 从 configure.py 写入的 config 文件中读取所有构建参数
config.parse()
# 检查 Python 环境（确保 Python3 可用）
base.check_python()

base_dir = base.get_script_dir(__file__)

# 设置当前构建平台环境变量
base.set_env("BUILD_PLATFORM", config.option("platform"))

# ---- 品牌定制处理 ----
# 如果配置了 branding 参数且当前不在品牌构建流程中
if ("1" != base.get_env("OO_RUNNING_BRANDING")) and ("" != config.option("branding")):
  branding_dir = base_dir + "/../" + config.option("branding")

  # 如果启用了仓库更新，克隆或更新品牌仓库
  if ("1" == config.option("update")):
    is_exist = True
    if not base.is_dir(branding_dir):
      is_exist = False
      base.cmd("git", ["clone", config.option("branding-url"), branding_dir])

    base.cmd_in_dir(branding_dir, "git", ["fetch"], True)

    if not is_exist or ("1" != config.option("update-light")):
      base.cmd_in_dir(branding_dir, "git", ["checkout", "-f", config.option("branch")], True)

    base.cmd_in_dir(branding_dir, "git", ["pull"], True)

  # 如果品牌目录下有独立的 make.py，递归调用品牌构建并退出当前流程
  if base.is_file(branding_dir + "/build_tools/make.py"):
    base.check_build_version(branding_dir + "/build_tools")
    base.set_env("OO_RUNNING_BRANDING", "1")
    base.set_env("OO_BRANDING", config.option("branding"))
    base.cmd_in_dir(branding_dir + "/build_tools", "python", ["make.py"])
    exit(0)

# ---- 第 2 步：修正默认值 ----
# 品牌仓库已更新后，重新解析 defaults 文件中的默认参数
config.parse_defaults()

# 校验 build_tools 版本
base.check_build_version(base_dir)

# ---- 第 3 步：更新仓库 ----
# 如果启用了更新，克隆/拉取所有需要的 Git 仓库
if ("1" == config.option("update")):
  repositories = base.get_repositories()
  base.update_repositories(repositories)

# 配置通用应用程序环境（7z, curl 等工具的 PATH）
base.configure_common_apps()

# ---- 第 4 步：开发模式 ----
# develop=1 时进入开发模式，内部会自动 exit(0)，不执行后续步骤
develop.make()

# ---- 第 5 步：仅构建 JS ----
# 环境变量 OO_ONLY_BUILD_JS=1 时只构建 JS 资源，跳过 C++ 编译
if ("1" == base.get_env("OO_ONLY_BUILD_JS")):
  build_js.make()
  exit(0)

# ---- 第 6 步：编译 Core 第三方依赖库 ----
# 编译 boost, icu, v8, openssl, hunspell 等第三方库
make_common.make()

# ---- 第 7 步：Desktop 专属配置（仅 Windows） ----
# 为桌面版构建 updmodule（Windows 自动更新模块）
if config.check_option("module", "desktop"):
  config.extend_option("qmake_addon", "URL_WEBAPPS_HELP=https://download.onlyoffice.com/install/desktop/editors/help/v" + base.get_env('PRODUCT_VERSION') + "/apps")

  if "windows" == base.host_platform():
    config.extend_option("config", "updmodule")
    # 设置桌面版更新检查 URL（正式版和开发版）
    base.set_env("DESKTOP_URL_UPDATES_MAIN_CHANNEL", "https://download.onlyoffice.com/install/desktop/editors/windows/onlyoffice/appcast.json")
    base.set_env("DESKTOP_URL_UPDATES_DEV_CHANNEL", "https://download.onlyoffice.com/install/desktop/editors/windows/onlyoffice/appcastdev.json")

# ---- 第 8 步：编译 C++ 解决方案 ----
# 通过 qmake 生成 Makefile，然后 make 编译所有 C++ 项目
build_sln.make()

# ---- 第 9 步：编译 JavaScript ----
# 通过 grunt 构建 sdkjs 和 web-apps
build_js.make()

# ---- 第 10 步：打包 Server ----
# 通过 pkg 将 Node.js 服务打包为独立二进制文件
build_server.make()

# ---- 第 11 步：部署 ----
# 将所有构建产物复制到 out/ 输出目录
deploy.make()
