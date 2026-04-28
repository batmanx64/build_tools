#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
config.py - 构建系统配置管理模块
=================================
功能：从 config 文件中读取配置参数，提供参数查询和扩展方法。
所有选项以 "OO_" 为前缀写入环境变量，例如 --module="server" 变为 OO_MODULE=server。

关键函数：
    parse()          - 读取 config 文件并设置环境变量
    parse_defaults() - 读取 defaults 文件中的默认值，覆盖 config 中的 "default" 占位符
    check_option()   - 检查某个选项是否包含特定值
    option()         - 获取某个选项的值
    extend_option()  - 向某个选项追加值
    set_option()     - 设置某个选项的值
    check_compiler() - 根据平台自动检测编译器类型
"""

import base
import os
import platform

def parse():
    """
    主配置解析函数。
    读取 build_tools/config 文件（由 configure.py 生成），将所有参数加载到内存并设置环境变量。
    同时处理平台别名（native/all/windows/linux/mac/android）的展开和编译器检测。
    """
    configfile = open(base.get_script_dir() + "/../config", "r")
    configOptions = {}
    for line in configfile:
        name, value = line.partition("=")[::2]
        k = name.strip()
        v = value.strip(" '\"\r\n")
        # 标准化布尔值：true/false → 1/0
        if ("true" == v.lower()):
            v = "1"
        if ("false" == v.lower()):
            v = "0"
        configOptions[k] = v
        # 以 OO_ 前缀写入环境变量，方便其他脚本读取
        os.environ["OO_" + k.upper().replace("-", "_")] = v

    # 导出到模块全局变量
    global options
    options = configOptions

    # 所有支持的平台列表
    global platforms
    platforms = ["win_64", "win_32", "win_64_xp", "win_32_xp", "win_arm64",
                 "linux_64", "linux_32", "linux_arm64",
                 "mac_64", "mac_arm64",
                 "ios",
                 "android_arm64_v8a", "android_armv7", "android_x86", "android_x86_64"]

    # ---- 展开平台别名 ----
    host_platform = base.host_platform()

    # "all" = 当前平台的所有变体（如 Linux 上展开为 linux_64 linux_32）
    if check_option("platform", "all"):
        if ("windows" == host_platform):
            options["platform"] += " win_64 win_32"
        elif ("linux" == host_platform):
            options["platform"] += " linux_64 linux_32"
        else:
            options["platform"] += " mac_64"

    # "native" = 自动检测当前系统的位宽
    if check_option("platform", "native"):
        bits = "32"
        if platform.machine().endswith('64'):
            bits = "64"
        if ("windows" == host_platform):
            options["platform"] += (" win_" + bits)
        elif ("linux" == host_platform):
            options["platform"] += (" linux_" + bits)
        else:
            options["platform"] += (" mac_" + bits)

    # macOS 上处理 Apple Silicon 的特殊逻辑：
    # 在 Intel Mac 上构建 arm64 也需要包含 x86_64
    if ("mac" == host_platform) and check_option("platform", "mac_arm64") and not base.is_os_arm():
        if not check_option("platform", "mac_64"):
            options["platform"] = "mac_64 " + options["platform"]

    # Windows XP 平台别名展开
    if check_option("platform", "xp") and ("windows" == host_platform):
        options["platform"] += " win_64_xp win_32_xp"

    # Android 平台别名展开（四个架构）
    if check_option("platform", "android"):
        options["platform"] += " android_arm64_v8a android_armv7 android_x86 android_x86_64"

    # ---- VS 版本自动检测 ----
    if ("windows" == host_platform) and ("" == option("vs-version")):
        options["vs-version"] = "2019"
        # XP 目标只能用 VS 2015
        if check_option("platform", "win_64_xp") or check_option("platform", "win_32_xp"):
            options["vs-version"] = "2015"

    if ("windows" == host_platform) and ("2019" == option("vs-version")):
        extend_option("config", "vs2019")

    # ---- Sysroot 配置（Linux 专用） ----
    # 非 Linux 平台忽略 sysroot
    if "linux" != host_platform and "sysroot" in options:
        options["sysroot"] = ""

    if "linux" == host_platform and "sysroot" in options:
        if options["sysroot"] == "0":
            options["sysroot"] = ""
        elif options["sysroot"] == "1":
            # 自动下载并解压 sysroot（Ubuntu 16.04 用于兼容性）
            dst_dir = os.path.abspath(base.get_script_dir(__file__) + '/../tools/linux/sysroot')
            dst_dir_amd64 = dst_dir + "/ubuntu16-amd64-sysroot"
            dst_dir_arm64 = dst_dir + "/ubuntu16-arm64-sysroot"
            if not base.is_dir(dst_dir_amd64) or not base.is_dir(dst_dir_arm64):
                base.cmd_in_dir(dst_dir, "python3", ["./fetch.py", "all"])
            options["sysroot_linux_64"] = dst_dir_amd64
            options["sysroot_linux_arm64"] = dst_dir_arm64
        else:
            # 自定义 sysroot 路径，只构建单一平台
            options["sysroot"] = "1"
            options["sysroot_linux_64"] = options["sysroot"]
            options["sysroot_linux_arm64"] = options["sysroot"]

    # 自动检测需要使用的 CEF/V8 版本（基于 GCC 版本）
    if is_cef_107():
        extend_option("config", "cef_version_107")
    if is_v8_60():
        extend_option("config", "v8_version_60")

    # ---- VS 路径自动检测（Windows） ----
    if ("windows" == host_platform) and ("" == option("vs-path")):
        programFilesDir = base.get_env("ProgramFiles")
        if ("" != base.get_env("ProgramFiles(x86)")):
            programFilesDir = base.get_env("ProgramFiles(x86)")
        if ("2015" == options["vs-version"]):
            options["vs-path"] = programFilesDir + "/Microsoft Visual Studio 14.0/VC"
        elif ("2019" == options["vs-version"]):
            if base.is_dir(programFilesDir + "/Microsoft Visual Studio/2019/Enterprise/VC/Auxiliary/Build"):
                options["vs-path"] = programFilesDir + "/Microsoft Visual Studio/2019/Enterprise/VC/Auxiliary/Build"
            elif base.is_dir(programFilesDir + "/Microsoft Visual Studio/2019/Professional/VC/Auxiliary/Build"):
                options["vs-path"] = programFilesDir + "/Microsoft Visual Studio/2019/Professional/VC/Auxiliary/Build"
            else:
                options["vs-path"] = programFilesDir + "/Microsoft Visual Studio/2019/Community/VC/Auxiliary/Build"

    # ---- 插件默认值 ----
    if not "sdkjs-plugin" in options:
        options["sdkjs-plugin"] = "default"
    if not "sdkjs-plugin-server" in options:
        options["sdkjs-plugin-server"] = "default"

    # ---- iOS 框架配置 ----
    if check_option("platform", "ios"):
        if not check_option("config", "no_bundle_xcframeworks"):
            if not check_option("config", "bundle_xcframeworks"):
                extend_option("config", "bundle_xcframeworks")

    if check_option("config", "bundle_xcframeworks"):
        if not check_option("config", "bundle_dylibs"):
            extend_option("config", "bundle_dylibs")

    # macOS 桌面版默认启用 bundle_dylibs
    if ("mac" == host_platform) and check_option("module", "desktop"):
        if not check_option("config", "bundle_dylibs"):
            extend_option("config", "bundle_dylibs")

    # ---- 使用系统 Qt ----
    if check_option("use-system-qt", "1"):
        base.cmd_in_dir(base.get_script_dir() + "/../tools/linux", "python", ["use_system_qt.py"])
        options["qt-dir"] = base.get_script_dir() + "/../tools/linux/system_qt"

    # ---- 警告控制 ----
    # 默认禁用所有警告，除非明确启用
    if not check_option("config", "core_enable_all_warnings"):
        extend_option("config", "core_disable_all_warnings")

    return


def check_compiler(platform):
    """
    根据目标平台自动选择编译器。
    Windows → msvc<version>[_64|_arm64]
    Linux   → gcc[_64|_arm|_arm64]
    Mac     → clang[_64]
    iOS     → ios
    Android → platform name
    """
    compiler = {}
    compiler["compiler"] = option("compiler")
    compiler["compiler_64"] = compiler["compiler"] + "_64"

    if ("" != compiler["compiler"]):
        if ("ios" == platform):
            compiler["compiler_64"] = compiler["compiler"]
        return compiler

    if (0 == platform.find("win")):
        compiler["compiler"] = "msvc" + options["vs-version"]
        compiler["compiler_64"] = "msvc" + options["vs-version"] + "_64"
        if (0 == platform.find("win_arm")):
            compiler["compiler"] = "msvc" + options["vs-version"] + "_arm"
            compiler["compiler_64"] = "msvc" + options["vs-version"] + "_arm64"
    elif (0 == platform.find("linux")):
        compiler["compiler"] = "gcc"
        compiler["compiler_64"] = "gcc_64"
        if (0 == platform.find("linux_arm")) and not base.is_os_arm():
            compiler["compiler"] = "gcc_arm"
            compiler["compiler_64"] = "gcc_arm64"
    elif (0 == platform.find("mac")):
        compiler["compiler"] = "clang"
        compiler["compiler_64"] = "clang_64"
    elif ("ios" == platform):
        compiler["compiler"] = "ios"
        compiler["compiler_64"] = "ios"
    elif (0 == platform.find("android")):
        compiler["compiler"] = platform
        compiler["compiler_64"] = platform

    # macOS 上 Qt 可能使用 macos 文件夹命名
    if base.host_platform() == "mac":
        if not base.is_dir(options["qt-dir"] + "/" + compiler["compiler_64"]):
            if base.is_dir(options["qt-dir"] + "/macos"):
                compiler["compiler"] = "macos"
                compiler["compiler_64"] = "macos"

    return compiler


def check_option(name, value):
    """检查某个选项是否包含指定的值。使用空格分隔的单词匹配。"""
    if not name in options:
        return False
    tmp = " " + options[name] + " "
    if (-1 == tmp.find(" " + value + " ")):
        return False
    return True


def option(name):
    """获取选项值，不存在则返回空字符串。"""
    if name in options:
        return options[name]
    return ""


def extend_option(name, value):
    """向已有选项追加值（空格分隔），不存在则新建。"""
    if name in options:
        options[name] = options[name] + " " + value
    else:
        options[name] = value


def set_option(name, value):
    """直接设置选项值（覆盖）。"""
    options[name] = value


def branding():
    """获取品牌名称，未指定则默认为 onlyoffice。"""
    branding = option("branding-name")
    if ("" == branding):
        branding = "onlyoffice"
    return branding


def is_mobile_platform():
    """检查当前是否在构建移动端平台。"""
    all_platforms = option("platform")
    if (-1 != all_platforms.find("android")):
        return True
    if (-1 != all_platforms.find("ios")):
        return True
    return False


def get_custom_sysroot_bin(platform):
    """获取 sysroot 的 bin 目录路径。"""
    use_platform = platform
    if "linux_arm64" == platform and not base.is_os_arm():
        use_platform = "linux_64"
    return option("sysroot_" + use_platform) + "/usr/bin"


def get_custom_sysroot_lib(platform, isNatural=False):
    """获取 sysroot 的库目录路径。"""
    use_platform = platform
    if "linux_arm64" == platform and not base.is_os_arm() and not isNatural:
        use_platform = "linux_64"

    if ("linux_64" == use_platform):
        return option("sysroot_linux_64") + "/usr/lib/x86_64-linux-gnu"
    if ("linux_arm64" == use_platform):
        return option("sysroot_linux_arm64") + "/usr/lib/aarch64-linux-gnu"
    return ""


def parse_defaults():
    """
    解析 defaults 文件中的默认参数。
    将 config 选项中的 "default" 占位符替换为 defaults 中的实际值。
    支持 branding 目录下独立的 defaults 文件。
    """
    defaults_path = base.get_script_dir() + "/../defaults"
    if ("" != option("branding")):
        defaults_path_branding = base.get_script_dir() + "/../../" + option("branding") + "/build_tools/defaults"
        if base.is_file(defaults_path_branding):
            defaults_path = defaults_path_branding
    defaults_file = open(defaults_path, "r")
    defaults_options = {}
    for line in defaults_file:
        name, value = line.partition("=")[::2]
        k = name.strip()
        v = value.strip(" '\"\r\n")
        if ("true" == v.lower()):
            v = "1"
        if ("false" == v.lower()):
            v = "0"
        defaults_options[k] = v

    # 用 defaults 值替换 config 中的 "default" 占位符
    for name in defaults_options:
        if name in options:
            options[name] = options[name].replace("default", defaults_options[name])
        else:
            options[name] = defaults_options[name]

    if ("config_addon" in defaults_options):
        extend_option("config", defaults_options["config_addon"])

    return


def is_cef_107():
    """
    判断是否需要使用 CEF 107（Chromium Embedded Framework 版本）。
    旧版 GCC（<5.4）不支持较新的 CEF 版本，需要回退到 CEF 107。
    """
    if ("linux" == base.host_platform()) and (5004 > base.get_gcc_version()) and not check_option("platform", "android"):
        return True
    return False


def is_v8_60():
    """
    判断是否需要使用 V8 v6.0 替代较新的版本。
    旧编译环境（GCC < 5.4 或 VS 2015）不支持更新的 V8。
    """
    if check_option("platform", "linux_arm64"):
        return False

    if ("linux" == base.host_platform()) and (5004 > base.get_gcc_version()) and not check_option("platform", "android"):
        return True

    if ("windows" == base.host_platform()) and ("2015" == option("vs-version")):
        return True

    return False
