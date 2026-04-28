#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
build_server.py - Server 服务构建模块
=======================================
功能：将 Node.js 编写的 server 服务（DocService、FileConverter、Metrics 等）
通过 pkg 工具打包为独立的可执行二进制文件。

核心流程：
  1. 更新版本号到源码中
  2. 安装 npm 依赖 (npm ci)
  3. 执行编译 (npm run build)
  4. 使用 pkg 打包为独立二进制文件

技术说明：
  - pkg 目标格式：node20-<os>[-<arch>]
  - 使用 6GB 堆内存限制 (max_old_space_size=6144)
  - 支持 server addon 的构建
"""

import config
import base
import datetime


def make():
    """
    主入口：构建并打包 Server 服务。
    仅当 --module 包含 "server" 时执行。
    """
    if(not config.check_option("module", "server")):
        return

    git_dir = base.get_script_dir() + "/../.."
    server_dir = base.get_script_dir() + "/../../server"
    server_admin_panel_dir = base.get_script_dir() + "/../../server-admin-panel"
    branding_dir = server_dir + "/branding"

    if("" != config.option("branding")):
        branding_dir = git_dir + '/' + config.option("branding") + '/server'

    # 安装依赖并构建 addon
    build_server_with_addons()

    # ---- 版本号替换 ----
    product_version = base.get_env('PRODUCT_VERSION')
    if(not product_version):
        product_version = "0.0.0"

    build_number = base.get_env('BUILD_NUMBER')
    if(not build_number):
        build_number = "0"

    cur_date = datetime.date.today().strftime("%m/%d/%Y")

    # 将版本号和构建日期写入 JS 源码
    base.replaceInFileRE(server_dir + "/Common/sources/commondefines.js", "const buildNumber = [0-9]*", "const buildNumber = " + build_number)
    base.replaceInFileRE(server_dir + "/Common/sources/license.js", "const buildDate = '[0-9-/]*'", "const buildDate = '" + cur_date + "'")
    base.replaceInFileRE(server_dir + "/Common/sources/commondefines.js", "const buildVersion = '[0-9.]*'", "const buildVersion = '" + product_version + "'")

    # 品牌定制公钥
    custom_public_key = branding_dir + '/debug.js'

    if(base.is_exist(custom_public_key)):
        base.copy_file(custom_public_key, server_dir + '/Common/sources')

    # ---- 设置 pkg 目标平台 ----
    pkg_target = "node20"

    if ("linux" == base.host_platform()):
        pkg_target += "-linux"
        if (-1 != config.option("platform").find("linux_arm64")):
            pkg_target += "-arm64"

    if ("windows" == base.host_platform()):
        pkg_target += "-win"

    # ---- 使用 pkg 打包各服务 ----
    base.cmd_in_dir(server_dir + "/DocService", "pkg", [".", "-t", pkg_target, "--options", "max_old_space_size=6144", "-o", "docservice"])
    base.cmd_in_dir(server_dir + "/FileConverter", "pkg", [".", "-t", pkg_target, "-o", "converter"])
    base.cmd_in_dir(server_dir + "/Metrics", "pkg", [".", "-t", pkg_target, "-o", "metrics"])
    # 可选的管理面板
    if "server-admin-panel" in base.get_server_addons() and base.is_exist(server_admin_panel_dir):
        base.cmd_in_dir(server_admin_panel_dir + "/server", "pkg", [".", "-t", pkg_target, "-o", "adminpanel"])

    # 打包 Node.js 示例程序
    example_dir = base.get_script_dir() + "/../../document-server-integration/web/documentserver-example/nodejs"
    base.delete_dir(example_dir  + "/node_modules")
    base.cmd_in_dir(example_dir, "npm", ["ci"])
    base.cmd_in_dir(example_dir, "pkg", [".", "-t", pkg_target, "-o", "example"])


def build_server_with_addons():
    """
    安装 Server 及所有 addon 的 npm 依赖并执行编译。
    对所有 server addon（如 server-lockstorage 等）执行 npm ci + npm run build。
    """
    addons = {}
    addons["server"] = [True, False]
    addons.update(base.get_server_addons())
    for addon in addons:
        if (addon):
            addon_dir = base.get_script_dir() + "/../../" + addon
            if (base.is_exist(addon_dir)):
                base.cmd_in_dir(addon_dir, "npm", ["ci"])
                base.cmd_in_dir(addon_dir, "npm", ["run", "build"])


def build_server_develop():
    """开发模式构建 Server（安装依赖但不打包）。"""
    build_server_with_addons()
