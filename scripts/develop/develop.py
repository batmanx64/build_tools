#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
develop.py - 开发模式构建入口
===============================
功能：当 --develop=1 时被 make.py 调用，执行开发模式构建流程。
开发模式特点：
  - 不编译 C++（下载预编译二进制）
  - JS 不做压缩混淆（方便调试）
  - 自动检查并安装系统依赖
  - Server 不打包（直接通过 Node.js 运行）

流程：
  1. 检查系统依赖（PostgreSQL、RabbitMQ、Node.js 等）
  2. 构建开发版 Server（npm install + npm run build）
  3. 构建开发版 JS（无压缩）
  4. 下载预编译 Core 二进制并配置服务器
  5. 退出（不执行后续的 C++ 编译阶段）
"""

import sys
sys.path.append('scripts')
sys.path.append('scripts/develop')
import base
import build_js
import build_server
import config
import dependence
import config_server as develop_config_server

base_dir = base.get_script_dir(__file__)


def build_docker_server():
    """Docker 开发模式：检查 Docker 依赖并构建开发版 Server。"""
    dependence.check__docker_dependencies()
    build_develop_server()


def build_docker_sdk_web_apps(dir):
    """Docker 开发模式：构建 SDKJS 和 Web-Apps。"""
    dependence.check__docker_dependencies()
    build_js.build_js_develop(dir)


def build_develop_server():
    """构建开发版 Server（安装依赖 + 下载 Core 二进制 + 生成配置）。"""
    build_server.build_server_develop()
    build_js.build_js_develop(base_dir + "/../../..")
    develop_config_server.make()
    # 如果有品牌定制，调用品牌的 develop 脚本
    if ("" != config.option("branding")):
        branding_develop_script_dir = base_dir + "/../../../" + config.option("branding") + "/build_tools/scripts"
        if base.is_file(branding_develop_script_dir + "/develop.py"):
            base.cmd_in_dir(branding_develop_script_dir, "python", ["develop.py"], True)


def make():
    """
    主入口：如果 --develop=1，执行开发模式构建后退出。
    如果 --develop=0（生产模式），直接返回，不执行任何操作。
    """
    if ("1" != config.option("develop")):
        return
    if not dependence.check_dependencies():
        exit(1)
    build_develop_server()
    exit(0)
