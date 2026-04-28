#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
deploy_core.py - Core 部署脚本
===============================
功能：将 Core C++ 层的构建产物按平台部署到 out/<platform>/<branding>/core 目录。
包括所有格式处理动态库、x2t 转换器、测试工具、字体生成工具、JS 缓存等。
"""

import config
import base
import os

def make():
    """主入口：遍历目标平台，执行 Core 部署。"""
    base_dir = base.get_script_dir() + "/../out"
    git_dir = base.get_script_dir() + "/../.."
    core_dir = git_dir + "/core"
    core_build_dir = core_dir + "/build"
    branding = config.branding()
    if ("" != config.option("branding")):
        core_build_dir += ("/" + config.option("branding"))

    platforms = config.option("platform").split()
    for native_platform in platforms:
        if not native_platform in config.platforms:
            continue

        archive_dir = base_dir + ("/" + native_platform + "/" + branding + "/core")
        if (base.is_dir(archive_dir)):
            base.delete_dir(archive_dir)
        base.create_dir(archive_dir)

        platform = native_platform
        platform_postfix = platform + base.qt_dst_postfix()
        isWindowsXP = False if (-1 == native_platform.find("_xp")) else True

        # ---- 复制所有 Core 动态库（文档格式引擎） ----
        base.copy_lib(core_build_dir + "/lib/" + platform_postfix, archive_dir, "kernel")
        base.copy_lib(core_build_dir + "/lib/" + platform_postfix, archive_dir, "kernel_network")
        base.copy_lib(core_build_dir + "/lib/" + platform_postfix, archive_dir, "graphics")
        base.copy_lib(core_build_dir + "/lib/" + platform_postfix, archive_dir, "doctrenderer")
        base.copy_lib(core_build_dir + "/lib/" + platform_postfix, archive_dir, "DjVuFile")
        base.copy_lib(core_build_dir + "/lib/" + platform_postfix, archive_dir, "XpsFile")
        base.copy_lib(core_build_dir + "/lib/" + platform_postfix, archive_dir, "OFDFile")
        base.copy_lib(core_build_dir + "/lib/" + platform_postfix, archive_dir, "PdfFile")
        base.copy_lib(core_build_dir + "/lib/" + platform_postfix, archive_dir, "HtmlFile2")
        base.copy_lib(core_build_dir + "/lib/" + platform_postfix, archive_dir, "UnicodeConverter")
        base.copy_lib(core_build_dir + "/lib/" + platform_postfix, archive_dir, "Fb2File")
        base.copy_lib(core_build_dir + "/lib/" + platform_postfix, archive_dir, "EpubFile")
        base.copy_lib(core_build_dir + "/lib/" + platform_postfix, archive_dir, "IWorkFile")
        base.copy_lib(core_build_dir + "/lib/" + platform_postfix, archive_dir, "HWPFile")
        base.copy_lib(core_build_dir + "/lib/" + platform_postfix, archive_dir, "DocxRenderer")
        base.copy_lib(core_build_dir + "/lib/" + platform_postfix, archive_dir, "hunspell")
        base.copy_lib(core_build_dir + "/lib/" + platform_postfix, archive_dir, "StarMathConverter")
        base.copy_lib(core_build_dir + "/lib/" + platform_postfix, archive_dir, "ooxmlsignature", "xp" if isWindowsXP else "")
        base.copy_file(git_dir + "/sdkjs/pdf/src/engine/cmap.bin", archive_dir + "/cmap.bin")
        base.copy_exe(core_build_dir + "/bin/" + platform_postfix, archive_dir, "x2t")

        # ---- JS 资源（sdkjs） ----
        base.copy_dir(base_dir + "/js/" + branding + "/builder/sdkjs", archive_dir + "/sdkjs")
        base.create_dir(archive_dir + "/sdkjs/vendor")
        base.copy_dir(base_dir + "/js/" + branding + "/builder/web-apps/vendor/jquery", archive_dir + "/sdkjs/vendor/jquery")
        base.copy_dir(base_dir + "/js/" + branding + "/builder/web-apps/vendor/xregexp", archive_dir + "/sdkjs/vendor/xregexp")

        # ---- ICU 国际化数据 ----
        if ("windows" == base.host_platform()):
            base.copy_files(core_dir + "/Common/3dParty/icu/" + platform + "/build/*.dll", archive_dir + "/")
        else:
            if not (0 == platform.find("mac") and config.check_option("config", "bundle_dylibs")):
                base.copy_files(core_dir + "/Common/3dParty/icu/" + platform + "/build/*", archive_dir + "/")
        base.copy_v8_files(core_dir, archive_dir, platform)

        # ---- 部署工具（字体生成、插件管理、测试等） ----
        base.copy_exe(core_build_dir + "/bin/" + platform_postfix, archive_dir, "allfontsgen")
        base.copy_exe(core_build_dir + "/bin/" + platform_postfix, archive_dir, "allthemesgen")
        base.copy_exe(core_build_dir + "/bin/" + platform_postfix, archive_dir, "pluginsmanager")
        base.copy_exe(core_build_dir + "/bin/" + platform_postfix, archive_dir, "standardtester")
        base.copy_exe(core_build_dir + "/bin/" + platform_postfix, archive_dir, "x2ttester")
        base.copy_exe(core_build_dir + "/bin/" + platform_postfix, archive_dir, "ooxml_crypt")
        base.copy_exe(core_build_dir + "/bin/" + platform_postfix, archive_dir, "vboxtester")
        base.copy_exe(core_build_dir + "/bin/" + platform_postfix, archive_dir, "metafiletester")
        base.copy_exe(core_build_dir + "/bin/" + platform_postfix, archive_dir, "dictionariestester")

        # ---- macOS Framework 修正 ----
        if (0 == platform.find("mac")):
            base.for_each_framework(archive_dir, "mac", callbacks=[base.generate_plist], max_depth=1)
            base.mac_correct_rpath_x2t(archive_dir)

        # ---- 生成 x2t JS 缓存 ----
        base.generate_doctrenderer_config(archive_dir + "/DoctRenderer.config", "./", "builder", "", "./dictionaries")
        base.create_x2t_js_cache(archive_dir, "core", platform)
        base.delete_file(archive_dir + "/DoctRenderer.config")

        # ---- 字典（拼写检查，无压缩且不包含"添加到字典"） ----
        base.copy_dictionaries(git_dir + "/dictionaries", archive_dir + "/dictionaries", True, False)
    return
