#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
qmake.py - QMake 编译执行模块
===============================
功能：对指定的 .pro 项目文件执行 qmake → make 编译流程。
支持多平台、sysroot 交叉编译、多种编译器。

编译流程：
  1. 检查目标平台是否受支持（Qt 环境是否存在）
  2. 设置 Qt 环境变量
  3. 执行 qmake -nocache 生成 Makefile（传递 CONFIG 参数）
  4. 执行 make -f Makefile.<suffix> 编译
  5. Linux 上支持 sysroot 交叉编译环境设置
  6. Windows 上通过 vcvarsall.bat 设置 VS 环境
"""

import os
import sys

__dir__name__ = os.path.dirname(__file__)
sys.path.append(__dir__name__ + '/core_common/modules/android')

import base
import config
import android_ndk
import multiprocessing


def get_make_file_suffix(platform):
    """生成 Makefile 的后缀名：<platform>[_debug_][<branding>]。"""
    suffix = platform
    if config.check_option("config", "debug"):
        suffix += "_debug_"
    suffix += config.option("branding")
    return suffix


def get_j_num():
    """获取 make 的 -j（并行数）参数。multiprocess=0 返回空列表（单进程）。"""
    if ("0" != config.option("multiprocess")):
        return ["-j" + str(multiprocessing.cpu_count())]
    return []


def check_support_platform(platform):
    """检查目标平台是否受 Qt 支持（qmake 可执行文件是否存在）。"""
    qt_dir = base.qt_setup(platform)
    if not base.is_file(qt_dir + "/bin/qmake") and not base.is_file(qt_dir + "/bin/qmake.exe") and not base.is_file(qt_dir + "/bin/qmake.bat"):
        return False
    return True


def make(platform, project, qmake_config_addon="", is_no_errors=False):
    """
    核心函数：对指定平台和 .pro 文件执行完整的 qmake → make 编译。

    参数：
        platform: 目标平台（如 linux_64, win_64, mac_64）
        project: .pro 文件路径
        qmake_config_addon: 额外的 qmake CONFIG 参数
        is_no_errors: 是否忽略编译错误
    """
    # 检查平台支持
    if not check_support_platform(platform):
        print("THIS PLATFORM IS NOT SUPPORTED")
        return

    old_env = dict(os.environ)

    # 设置 Qt 环境
    qt_dir = base.qt_setup(platform)
    base.set_env("OS_DEPLOY", platform)

    # 解析 .pro 文件路径
    file_pro = os.path.abspath(project)
    pro_dir = os.path.dirname(file_pro)
    if (pro_dir.endswith("/.")):
        pro_dir = pro_dir[:-2]
    if (pro_dir.endswith("/")):
        pro_dir = pro_dir[:-1]

    makefile_name = "Makefile." + get_make_file_suffix(platform)
    makefile = pro_dir + "/" + makefile_name
    stash_file = pro_dir + "/.qmake.stash"

    old_cur = os.getcwd()
    os.chdir(pro_dir)

    # 删除旧的临时文件
    if (base.is_file(stash_file)):
        base.delete_file(stash_file)
    if (base.is_file(makefile)):
        base.delete_file(makefile)

    base.set_env("DEST_MAKEFILE_NAME", "./" + makefile_name)

    # ---- Android NDK 环境设置 ----
    if (-1 != platform.find("android")):
        base.set_env("ANDROID_NDK_HOST", android_ndk.host["arch"])
        base.set_env("ANDROID_NDK_PLATFORM", "android-" + android_ndk.get_sdk_api())
        base.set_env("PATH", qt_dir + "/bin:" + android_ndk.toolchain_dir() + "/bin:" + base.get_env("PATH"))

    # ---- iOS 环境设置 ----
    if (-1 != platform.find("ios")):
        base.hack_xcode_ios()
        sdk_name = "iphoneos"
        if qmake_config_addon.find("ios_simulator") != -1:
            sdk_name = "iphonesimulator"
        base.set_env("SDK_PATH", base.find_ios_sdk(sdk_name))
        base.set_env("XCODE_TOOLCHAIN_PATH", base.find_xcode_toolchain(sdk_name))

    if base.is_file(makefile):
        base.delete_file(makefile)

    # 构建 qmake CONFIG 参数
    config_param = base.qt_config(platform)
    if ("" != qmake_config_addon):
        config_param += (" " + qmake_config_addon)

    # qmake 额外参数
    qmake_addon = []
    if ("" != config.option("qmake_addon")):
        qmake_addon = config.option("qmake_addon").split()

    # 构建清理和编译命令参数
    clean_params = ["clean", "-f", makefile]
    distclean_params = ["distclean", "-f", makefile]
    build_params = ["-nocache", file_pro] + base.qt_config_as_param(config_param) + qmake_addon

    qmake_app = qt_dir + "/bin/qmake"

    # ===================== 非 Windows 平台（Linux / macOS） =====================
    if not base.is_windows():
        # 如果有自定义 Qt 配置文件，指定 -qtconf
        if base.is_file(qt_dir + "/onlyoffice_qt.conf"):
            build_params.append("-qtconf")
            build_params.append(qt_dir + "/onlyoffice_qt.conf")
        if "1" == config.option("use-clang"):
            build_params.append("-spec")
            build_params.append("linux-clang-libc++")

        # ---- Sysroot 交叉编译环境 ----
        if "" != config.option("sysroot"):
            sysroot_path = config.option("sysroot_" + platform)
            os.environ['QMAKE_CUSTOM_SYSROOT'] = sysroot_path
            os.environ['QMAKE_CUSTOM_SYSROOT_BIN'] = config.get_custom_sysroot_bin(platform)
            os.environ['PKG_CONFIG_PATH'] = config.get_custom_sysroot_lib(platform, True) + "/pkgconfig"
            os.environ['PKG_CONFIG_SYSROOT_DIR'] = sysroot_path

        # 第 1 步：qmake 生成 Makefile
        base.cmd_exe(qmake_app, build_params)

        # 设置 sysroot 编译环境（CC、CXX、CFLAGS 等）
        if "" != config.option("sysroot"):
            base.set_sysroot_env(platform)

        base.correct_makefile_after_qmake(platform, makefile)

        # 第 2 步：make 编译（clean=1 时先清理再编译）
        if ("1" == config.option("clean")):
            base.cmd_and_return_cwd("make", clean_params, True)
            base.cmd_and_return_cwd("make", distclean_params, True)

            if "" != config.option("sysroot"):
                base.restore_sysroot_env()
            base.cmd(qmake_app, build_params)
            if "" != config.option("sysroot"):
                base.set_sysroot_env(platform)

            base.correct_makefile_after_qmake(platform, makefile)

        base.cmd_and_return_cwd("make", ["-f", makefile] + get_j_num(), is_no_errors)

        # 恢复 sysroot 前的环境
        if "" != config.option("sysroot"):
            base.restore_sysroot_env()

    # ===================== Windows 平台 =====================
    else:
        config_params_array = base.qt_config_as_param(config_param)
        config_params_string = ""
        for item in config_params_array:
            config_params_string += (" \"" + item + "\"")
        qmake_addon_string = " ".join(qmake_addon)
        if ("" != qmake_addon_string):
            qmake_addon_string = " " + qmake_addon_string

        # 选择 vcvarsall 架构参数
        vcvarsall_arch = "x64"
        if base.platform_is_32(platform):
            vcvarsall_arch = "x86"
        if (platform == "win_arm64"):
            vcvarsall_arch = "x64_arm64"

        qmake_env_addon = base.get_env("QT_QMAKE_ADDON")
        if (qmake_env_addon != ""):
            qmake_env_addon += " "

        # 构建 Windows 批处理脚本
        qmake_bat = []
        qmake_bat.append("call \"" + config.option("vs-path") + "/vcvarsall.bat\" " + vcvarsall_arch)
        qmake_addon_string = ""
        if ("" != config.option("qmake_addon")):
            qmake_addon_string = " " + (" ").join(["\"" + addon + "\"" for addon in qmake_addon])
        qmake_bat.append("call \"" + qmake_app + "\" -nocache " + qmake_env_addon + file_pro + config_params_string + qmake_addon_string)
        if ("1" == config.option("clean")):
            qmake_bat.append("call nmake " + " ".join(clean_params))
            qmake_bat.append("call nmake " + " ".join(distclean_params))
            qmake_bat.append("call \"" + qmake_app + "\" -nocache " + file_pro + config_params_string + qmake_addon_string)
        if ("0" != config.option("multiprocess")):
            qmake_bat.append("set CL=/MP")
        qmake_bat.append("call nmake -f " + makefile)
        base.run_as_bat(qmake_bat, is_no_errors)

    # 清理 .qmake.stash
    if (base.is_file(stash_file)):
        base.delete_file(stash_file)

    os.chdir(old_cur)

    # 恢复原始环境变量
    os.environ.clear()
    os.environ.update(old_env)
    return


def make_all_platforms(project, qmake_config_addon=""):
    """对所有目标平台执行 qmake 编译。"""
    platforms = config.option("platform").split()
    for platform in platforms:
        if not platform in config.platforms:
            continue
        print("------------------------------------------")
        print("BUILD_PLATFORM: " + platform)
        print("------------------------------------------")
        make(platform, project, qmake_config_addon)
    return
