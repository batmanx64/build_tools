#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
deploy.py - 部署模块入口
=========================
功能：根据 --module 参数调用对应产品的部署脚本，将构建产物复制到 out/ 输出目录。
"""

import config
import base
import deploy_desktop
import deploy_builder
import deploy_server
import deploy_core
import deploy_mobile
import deploy_osign


def make():
    """主入口：根据模块类型调用对应的部署脚本。"""
    if config.check_option("module", "desktop"):
        deploy_desktop.make()
    if config.check_option("module", "builder"):
        deploy_builder.make()
    if config.check_option("module", "server"):
        deploy_server.make()
    if config.check_option("module", "core"):
        deploy_core.make()
    if config.check_option("module", "mobile"):
        deploy_mobile.make()
    if config.check_option("module", "osign"):
        deploy_osign.make()
    # Windows ARM64 跨编译需要启动 QEMU 虚拟机完成部署
    if base.is_use_create_artifacts_qemu_any_platform():
        base.create_artifacts_qemu_any_platform()
    return
