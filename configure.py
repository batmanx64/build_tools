#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
configure.py - ONLYOFFICE 构建系统的配置入口脚本
==================================================
功能：解析用户传入的构建参数，并将所有参数写入 config 文件，供 make.py 读取使用。
该脚本不执行实际构建，只负责参数收集和持久化。

典型用法:
    python configure.py --update=1 --branch=master --module="server sdkjs web-apps" --platform=linux_64
    python configure.py --develop=1 --update=1 --module="desktop" --qt-dir="/path/to/qt" --clean=0
"""

import os
import sys
import optparse

arguments = sys.argv[1:]

# 创建参数解析器，定义所有支持的构建参数
parser = optparse.OptionParser()

# ---- 仓库更新相关 ----
# 是否更新/克隆仓库 (1=true, 0=false)，默认开启
parser.add_option("--update", action="store", type="string", dest="update", default="1",
    help="defines whether it's necessary to update/clone repos. If it's set to true (1 === true), build_tools automatically get the necessary subrepos. If it's set to false (0 === false), you should define which ones to use")
# 轻量更新：仅拉取不切换分支，避免本地修改丢失。仅在 update=1 时生效
parser.add_option("--update-light", action="store", type="string", dest="update-light", default="",
    help="performs pull/clone without switching branches, can be used only if update is true.")
# 目标分支/标签名，默认为 master
parser.add_option("--branch", action="store", type="string", dest="branch", default="master",
    help="branch/tag name, used only if update is true and update_light is not used. Updates/clones all the repos and switches the branch to the proper one deleting all the local changes")

# ---- 构建模式相关 ----
# 是否完全重新构建 (1=true)，开发模式下通常设为 0（增量构建）
parser.add_option("--clean", action="store", type="string", dest="clean", default="1",
    help="defines whether to build everything anew")
# 要构建的模块，多个模块用空格分隔：core, desktop, builder, server, mobile, osign
parser.add_option("--module", action="store", type="string", dest="module", default="builder",
    help="defines what modules to build. You can specify several of them, e.g. --module 'core desktop builder server mobile'")
# 开发模式开关 (0=生产模式, 1=开发模式)
parser.add_option("--develop", action="store", type="string", dest="develop", default="0",
    help="defines develop mode")
# 测试版模式开关 (0=正式版, 1=测试版)
parser.add_option("--beta", action="store", type="string", dest="beta", default="0",
    help="defines beta mode")

# ---- 平台与编译器 ----
# 目标平台，支持 native/all/windows/linux/mac/android 以及具体平台名
parser.add_option("--platform", action="store", type="string", dest="platform", default="native",
    help="defines the destination platform for your build ['win_64', 'win_32', 'win_64_xp', 'win_32_xp', 'win_arm64', 'linux_64', 'linux_32', 'mac_64', 'ios', 'android_arm64_v8a', 'android_armv7', 'android_x86', 'android_x86_64'; combinations: 'native': your current system (windows/linux/mac only); 'all': all available systems; 'windows': win_64 win_32 win_64_xp win_32_xp; 'linux': linux_64 linux_32; 'mac': mac_64; 'android': android_arm64_v8a android_armv7 android_x86 android_x86_64]")
# qmake 的额外配置参数，如 debug/release/updmodule 等
parser.add_option("--config", action="store", type="string", dest="config", default="",
    help="provides ability to specify additional parameters for qmake")
# Qt 目录路径，qmake 位于 qt-dir/compiler/bin 下
parser.add_option("--qt-dir", action="store", type="string", dest="qt-dir", default="",
    help="defines qmake directory path. qmake can be found in qt-dir/compiler/bin directory")
# Windows XP 专用 Qt 目录
parser.add_option("--qt-dir-xp", action="store", type="string", dest="qt-dir-xp", default="",
    help="defines qmake directory path for Windows XP. qmake can be found in 'qt-dir/compiler/bin directory")
# 外部文件夹路径（用于引用外部源码）
parser.add_option("--external-folder", action="store", type="string", dest="external-folder", default="",
    help="defines a directory with external folder")

# ---- 数据库相关 ----
# SQL 数据库类型（默认 postgres）
parser.add_option("--sql-type", action="store", type="string", dest="sql-type", default="postgres",
    help="defines the sql type wich will be used")
# 数据库端口（默认 5432）
parser.add_option("--db-port", action="store", type="string", dest="db-port", default="5432",
    help="defines the sql db-port wich will be used")
# 数据库名称（默认 onlyoffice）
parser.add_option("--db-name", action="store", type="string", dest="db-name", default="onlyoffice",
    help="defines the sql db-name wich will be used")
# 数据库用户名（默认 onlyoffice）
parser.add_option("--db-user", action="store", type="string", dest="db-user", default="onlyoffice",
    help="defines the sql db-user wich will be used")
# 数据库密码（默认 onlyoffice）
parser.add_option("--db-pass", action="store", type="string", dest="db-pass", default="onlyoffice",
    help="defines the sql db-pass wich will be used")

# ---- 编译器 ----
# 编译器名称，通常自动检测，不建议手动指定
parser.add_option("--compiler", action="store", type="string", dest="compiler", default="",
    help="defines compiler name. It is not recommended to use it as it's defined automatically (msvc2015, msvc2015_64, gcc, gcc_64, clang, clang_64, etc)")
# 禁用使用 Qt 的桌面应用 (0=不禁用, 1=禁用)
parser.add_option("--no-apps", action="store", type="string", dest="no-apps", default="0",
    help="disables building desktop apps that use qt")
# 演示文稿主题缩略图生成参数
parser.add_option("--themesparams", action="store", type="string", dest="themesparams", default="",
    help="provides settings for generating presentation themes thumbnails")

# ---- Git 协议 ----
# Git 协议选择：https / ssh / auto（自动检测）
parser.add_option("--git-protocol", action="store", type="string", dest="git-protocol", default="auto",
    help="can be used only if update is set to true - 'https', 'ssh'")

# ---- 品牌定制 ----
# 品牌目录路径
parser.add_option("--branding", action="store", type="string", dest="branding", default="",
    help="provides branding path")
# 品牌名称
parser.add_option("--branding-name", action="store", type="string", dest="branding-name", default="",
    help="provides branding name")
# 品牌仓库 URL
parser.add_option("--branding-url", action="store", type="string", dest="branding-url", default="",
    help="provides branding url")

# ---- 插件和 Addon ----
# SDKJS addon（可多次指定追加）
parser.add_option("--sdkjs-addon", action="append", type="string", dest="sdkjs-addons", default=[],
    help="provides sdkjs addons")
# 桌面端 SDKJS addon（可多次指定追加）
parser.add_option("--sdkjs-addon-desktop", action="append", type="string", dest="sdkjs-addons-desktop", default=[],
    help="provides sdkjs addons for desktop")
# Server addon（可多次指定追加）
parser.add_option("--server-addon", action="append", type="string", dest="server-addons", default=[],
    help="provides server addons")
# Web-Apps addon（可多次指定追加）
parser.add_option("--web-apps-addon", action="append", type="string", dest="web-apps-addons", default=[],
    help="provides web-apps addons")
# 通用插件列表（server 和 desktop 共用），默认值 "default"
parser.add_option("--sdkjs-plugin", action="append", type="string", dest="sdkjs-plugin", default=["default"],
    help="provides plugins for server-based and desktop versions of the editors")
# Server 端专用插件列表，默认值 "default"
parser.add_option("--sdkjs-plugin-server", action="append", type="string", dest="sdkjs-plugin-server", default=["default"],
    help="provides plugins for server-based version of the editors")

# ---- 特性与 Visual Studio ----
# 原生特性（作为 config addon 使用）
parser.add_option("--features", action="store", type="string", dest="features", default="",
    help="native features (config addon)")
# Visual Studio 版本（默认 2015）
parser.add_option("--vs-version", action="store", type="string", dest="vs-version", default="2015",
    help="version of visual studio")
# vcvarsall 路径（自动检测，通常不需要手动指定）
parser.add_option("--vs-path", action="store", type="string", dest="vs-path", default="",
    help="path to vcvarsall")

# ---- 服务器与网络 ----
# 站点 URL（默认 127.0.0.1）
parser.add_option("--siteUrl", action="store", type="string", dest="siteUrl", default="127.0.0.1",
    help="site url")

# ---- 性能 ----
# 是否启用多进程编译 (1=启用, 0=单进程)
parser.add_option("--multiprocess", action="store", type="string", dest="multiprocess", default="1",
    help="provides ability to specify single process for make")

# ---- Sysroot（Linux 专用） ----
# 使用 sysroot 构建 C++ 代码（保证旧系统兼容性）
# 设为 "1" 自动下载 Ubuntu 16.04 sysroot，也可以指定自定义路径
parser.add_option("--sysroot", action="store", type="string", dest="sysroot", default="0",
    help="provides ability to use sysroot (ubuntu 16.04) to build c++ code. If value is \"1\", then the sysroot from tools/linux/sysroot will be used, and if it is not there, it will download it and unpack it. You can also set value as the path to the your own sysroot (rarely used). Only for linux")

# ---- QEMU（Windows ARM64 交叉编译） ----
# QEMU 虚拟机目录，用于 win_arm64 在非 ARM 宿主机上的交叉编译
parser.add_option("--qemu-win-arm64-dir", action="store", type="string", dest="qemu-win-arm64-dir", default="",
    help="dir to qemu virtual machine for win_arm64 cross build. It should contains start.bat. More info in tools/win/qemu.")

# 解析命令行参数，转为字典
(options, args) = parser.parse_args(arguments)
configOptions = vars(options)

# 将解析后的参数写入 config 文件（make.py 和其他脚本会读取此文件）
configStore = open(os.path.dirname(os.path.realpath(__file__)) + "/config","w+")
for option in configOptions:
  writeOption = ""
  # 对于数组类型参数（如 addon），用 ", " 拼接
  if (isinstance(configOptions[option], list)):
    writeOption = ", ".join(configOptions[option])
  else:
    writeOption = configOptions[option]

  # 空值不写入文件
  if ("" != writeOption):
    configStore.write(option + "=\"" + writeOption + "\"\n")

configStore.close()
