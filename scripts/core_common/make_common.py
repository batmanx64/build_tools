#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
make_common.py - 第三方依赖库构建入口
=======================================
功能：按顺序构建所有 Core 所需的第三方依赖库。
包括：Boost、CEF、ICU、OpenSSL、V8、HTML2、iWork、Markdown、
Hunspell、HarfBuzz、GLEW、Hyphen、GoogleTest、Brotli、HEIF 等。
Android 平台额外构建 libcurl 和 WebSocket。
"""

import sys
sys.path.append('modules')
sys.path.append('..')

import config
import base
import glob

import boost
import cef
import icu
import openssl
import curl
import websocket_all
import v8
import html2
import iwork
import md
import hunspell
import glew
import harfbuzz
import oo_brotli
import hyphen
import googletest
import libvlc
import heif

def check_android_ndk_macos_arm(dir):
    """修复 macOS ARM 上 Android NDK 工具链路径问题：如果只有 x86_64 没有 arm64，则复制一份。"""
    if base.is_dir(dir + "/darwin-x86_64") and not base.is_dir(dir + "/darwin-arm64"):
        print("copy toolchain... [" + dir + "]")
        base.copy_dir(dir + "/darwin-x86_64", dir + "/darwin-arm64")
    return

def make():
    """主入口：按顺序构建所有第三方依赖库。"""
    # ---- 修复 Android NDK 在 macOS ARM 上的兼容性 ----
    if (config.check_option("platform", "android")) and (base.host_platform() == "mac") and (base.is_os_arm()):
        for toolchain in glob.glob(base.get_env("ANDROID_NDK_ROOT") + "/toolchains/*"):
            if base.is_dir(toolchain):
                check_android_ndk_macos_arm(toolchain + "/prebuilt")

    # ---- 构建所有第三方依赖库 ----
    boost.make()           # C++ 通用库（智能指针、正则等）
    cef.make()             # Chromium Embedded Framework（浏览器引擎）
    icu.make()             # Unicode 国际化支持
    openssl.make()         # SSL/TLS 加密库
    v8.make()              # JavaScript 引擎
    html2.make()           # HTML 解析/渲染
    iwork.make(False)      # Apple iWork 格式支持
    md.make()              # Markdown 解析
    hunspell.make(False)   # 拼写检查
    harfbuzz.make()        # 字体 shaping
    glew.make()            # OpenGL 扩展
    hyphen.make()          # 断字（连字）支持
    googletest.make()      # 测试框架
    oo_brotli.make()       # Brotli 压缩（Office Open XML）
    heif.make()            # HEIF 图片格式支持

    # VLC 视频播放器（可选）
    if config.check_option("build-libvlc", "1"):
        libvlc.make()

    # 移动端额外依赖
    if config.check_option("module", "mobile"):
        if (config.check_option("platform", "android")):
            curl.make()             # HTTP 网络库（Android 需要）
        websocket_all.make()        # WebSocket 支持
    return
