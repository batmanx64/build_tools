#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
update_js.py - JS 更新构建入口
===============================
功能：解析配置并调用 build_js.make() 执行 JS 构建。
作为单独入口脚本使用，独立于主构建流程。
"""

import config
import base
import build_js

config.parse()
build_js.make()
