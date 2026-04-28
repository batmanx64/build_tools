#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
build_sln.py - C++ 解决方案编译模块
=====================================
功能：读取 sln.json 中定义的项目列表，通过 qmake 生成 Makefile 并编译所有 C++ 项目。
这是构建系统中最核心的 C++ 编译阶段。

处理流程：
  1. 获取 --platform 参数中的所有目标平台
  2. 对每个平台，通过 sln.get_projects() 获取需要编译的 .pro 文件列表
  3. 对每个 .pro 文件，调用 qmake.make() 执行编译
"""

import config
import base
import os
import sys
sys.path.append(os.path.dirname(__file__) + "/..")
import sln
import qmake


def make(solution=""):
    """
    主入口：逐个编译 sln.json 中定义的所有 C++ 项目。
    对每个目标平台和每个项目执行 qmake → make 流程。
    """
    platforms = config.option("platform").split()
    for platform in platforms:
        if not platform in config.platforms:
            continue

        print("------------------------------------------")
        print("BUILD_PLATFORM: " + platform)
        print("------------------------------------------")

        # 读取 sln.json 中的项目列表，支持平台过滤和配置过滤
        if ("" == solution):
            solution = "./sln.json"
        projects = sln.get_projects(solution, platform)

        # 遍历所有需要编译的 .pro 项目文件
        for pro in projects:
            qmake_main_addon = ""
            # Android 特殊处理：Debug 模式下对 x2t 库启用 strip
            if (0 == platform.find("android")) and (-1 != pro.find("X2tConverter.pro")):
                if config.check_option("config", "debug") and not config.check_option("config", "disable_x2t_debug_strip"):
                    print("[WARNING:] temporary enable strip for x2t library in debug")
                    qmake_main_addon += "build_strip_debug"

            qmake.make(platform, pro, qmake_main_addon)
            # iOS 双架构（真机 + 模拟器）需要额外编译一次
            if config.check_option("platform", "ios") and config.check_option("config", "bundle_xcframeworks"):
                qmake.make(platform, pro, "xcframework_platform_ios_simulator")

    # ---- Builder 模块额外处理（Windows） ----
    # 检查并替换 unbranding 的 doctrenderer 库，构建 docbuilder.com/.net/.java 接口
    if config.check_option("module", "builder") and base.is_windows() and "onlyoffice" == config.branding():
        if (config.option("branding-name") == "onlyoffice"):
            for platform in platforms:
                if not platform in config.platforms:
                    continue
                core_lib_unbranding_dir = os.getcwd() + "/../core/build/lib/" + platform + base.qt_dst_postfix()
                if not base.is_dir(core_lib_unbranding_dir):
                    base.create_dir(core_lib_unbranding_dir)
                core_lib_branding_dir = os.getcwd() + "/../core/build/onlyoffice/lib/" + platform + base.qt_dst_postfix()
                base.copy_file(core_lib_branding_dir + "/doctrenderer.dll", core_lib_unbranding_dir + "/doctrenderer.dll")
                base.copy_file(core_lib_branding_dir + "/doctrenderer.lib", core_lib_unbranding_dir + "/doctrenderer.lib")

        # 修正 docbuilder.h 路径并编译 COM/NET 接口
        directory_builder_branding = os.getcwd() + "/../core/DesktopEditor/doctrenderer"
        if base.is_dir(directory_builder_branding):
            new_replace_path = base.correctPathForBuilder(directory_builder_branding + "/docbuilder.com/src/docbuilder.h")
            if ("2019" == config.option("vs-version")):
                base.make_sln_project("../core/DesktopEditor/doctrenderer/docbuilder.com/src", "docbuilder.com_2019.sln")
                if (True):
                    new_path_net = base.correctPathForBuilder(directory_builder_branding + "/docbuilder.net/src/docbuilder.net.cpp")
                    base.make_sln_project("../core/DesktopEditor/doctrenderer/docbuilder.net/src", "docbuilder.net.sln")
                    base.restorePathForBuilder(new_path_net)
            else:
                base.make_sln_project("../core/DesktopEditor/doctrenderer/docbuilder.com/src", "docbuilder.com.sln")
            base.restorePathForBuilder(new_replace_path)

    # 编译 Java docbuilder JNI 库和 JAR 包
    if config.check_option("module", "builder") and "onlyoffice" == config.branding():
        for platform in platforms:
            if not platform in config.platforms:
                continue
            qmake.make(platform, base.get_script_dir() + "/../../core/DesktopEditor/doctrenderer/docbuilder.java/src/jni/docbuilder_jni.pro", "", True)
            base.cmd_in_dir(base.get_script_dir() + "/../../core/DesktopEditor/doctrenderer/docbuilder.java", "python", ["make.py"])

    return
