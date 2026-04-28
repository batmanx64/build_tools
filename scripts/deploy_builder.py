#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
deploy_builder.py - Document Builder 部署脚本
===============================================
功能：将 Document Builder 的构建产物按平台部署到 out/<platform>/<branding>/documentbuilder 目录。
包括 Core 动态库、x2t 转换器、Python/Java 封装层、字体、字典等。
"""

import config
import base

def make():
    """主入口：遍历目标平台，执行 Document Builder 部署。"""
    base_dir = base.get_script_dir() + "/../out"
    git_dir = base.get_script_dir() + "/../.."
    core_dir = git_dir + "/core"
    branding = config.branding()

    platforms = config.option("platform").split()
    for native_platform in platforms:
        if not native_platform in config.platforms:
            continue

        root_dir = base_dir + ("/" + native_platform + "/" + branding + ("/DocumentBuilder" if base.is_windows() else "/documentbuilder"))
        root_dir_win64 = base_dir + "/win_64/" + branding + "/DocumentBuilder"
        if (base.is_dir(root_dir)):
            base.delete_dir(root_dir)
        base.create_dir(root_dir)

        qt_dir = base.qt_setup(native_platform)

        # ---- 检查是否是 Windows XP 平台 ----
        isWindowsXP = False if (-1 == native_platform.find("_xp")) else True
        platform = native_platform[0:-3] if isWindowsXP else native_platform

        core_build_dir = core_dir + "/build"
        if ("" != config.option("branding")):
            core_build_dir += ("/" + config.option("branding"))

        platform_postfix = platform + base.qt_dst_postfix()

        # ---- 复制 Core 动态库（x2t 依赖的所有格式引擎） ----
        base.copy_lib(core_build_dir + "/lib/" + platform_postfix, root_dir, "kernel")
        base.copy_lib(core_build_dir + "/lib/" + platform_postfix, root_dir, "UnicodeConverter")
        base.copy_lib(core_build_dir + "/lib/" + platform_postfix, root_dir, "kernel_network")
        base.copy_lib(core_build_dir + "/lib/" + platform_postfix, root_dir, "graphics")
        base.copy_lib(core_build_dir + "/lib/" + platform_postfix, root_dir, "PdfFile")
        base.copy_lib(core_build_dir + "/lib/" + platform_postfix, root_dir, "DjVuFile")
        base.copy_lib(core_build_dir + "/lib/" + platform_postfix, root_dir, "XpsFile")
        base.copy_lib(core_build_dir + "/lib/" + platform_postfix, root_dir, "OFDFile")
        base.copy_lib(core_build_dir + "/lib/" + platform_postfix, root_dir, "HtmlFile2")
        base.copy_lib(core_build_dir + "/lib/" + platform_postfix, root_dir, "Fb2File")
        base.copy_lib(core_build_dir + "/lib/" + platform_postfix, root_dir, "EpubFile")
        base.copy_lib(core_build_dir + "/lib/" + platform_postfix, root_dir, "IWorkFile")
        base.copy_lib(core_build_dir + "/lib/" + platform_postfix, root_dir, "HWPFile")
        base.copy_lib(core_build_dir + "/lib/" + platform_postfix, root_dir, "DocxRenderer")
        base.copy_lib(core_build_dir + "/lib/" + platform_postfix, root_dir, "StarMathConverter")
        base.copy_lib(core_build_dir + "/lib/" + platform_postfix, root_dir, "ooxmlsignature", "xp" if isWindowsXP else "")
        base.copy_file(git_dir + "/sdkjs/pdf/src/engine/cmap.bin", root_dir + "/cmap.bin")

        # ---- 复制 x2t 可执行文件 ----
        if ("ios" == platform):
            base.copy_lib(core_build_dir + "/lib/" + platform_postfix, root_dir, "x2t")
        else:
            base.copy_exe(core_build_dir + "/bin/" + platform_postfix, root_dir, "x2t")

        # ---- 部署 ICU 国际化数据 ----
        base.deploy_icu(core_dir, root_dir, native_platform)

        # ---- 部署 doctrenderer（文档渲染器） ----
        if isWindowsXP:
            base.copy_lib(core_build_dir + "/lib/" + platform_postfix + "/xp", root_dir, "doctrenderer")
            base.copy_file(core_build_dir + "/lib/" + platform_postfix + "/xp/doctrenderer.lib", root_dir + "/doctrenderer.lib")
        else:
            base.copy_lib(core_build_dir + "/lib/" + platform_postfix, root_dir, "doctrenderer")
            if (0 == platform.find("win")):
                base.copy_file(core_build_dir + "/lib/" + platform_postfix + "/doctrenderer.lib", root_dir + "/doctrenderer.lib")
        base.copy_v8_files(core_dir, root_dir, platform, isWindowsXP)

        # ---- Python 封装层 ----
        base.copy_lib(core_build_dir + "/lib/" + platform_postfix, root_dir, "docbuilder.c")
        base.copy_file(core_dir + "/DesktopEditor/doctrenderer/docbuilder.python/src/docbuilder.py", root_dir + "/docbuilder.py")

        # ---- Java 封装层（JNI） ----
        base.copy_lib(core_build_dir + "/lib/" + platform_postfix, root_dir, "docbuilder.jni")
        base.copy_file(core_dir + "/DesktopEditor/doctrenderer/docbuilder.java/build/libs/docbuilder.jar", root_dir + "/docbuilder.jar")

        # ---- app 主程序和配置 ----
        base.copy_exe(core_build_dir + "/bin/" + platform_postfix, root_dir, "docbuilder")
        base.generate_doctrenderer_config(root_dir + "/DoctRenderer.config", "./", "builder", "", "./dictionaries")
        base.copy_dir(git_dir + "/document-templates/new/en-US", root_dir + "/empty")

        # ---- 字典（拼写检查，无压缩且不包含"添加到字典"） ----
        base.copy_dictionaries(git_dir + "/dictionaries", root_dir + "/dictionaries", True, False)

        # ---- JS 资源 ----
        base.copy_dir(base_dir + "/js/" + branding + "/builder/sdkjs", root_dir + "/sdkjs")
        base.create_dir(root_dir + "/sdkjs/vendor")
        base.copy_dir(base_dir + "/js/" + branding + "/builder/web-apps/vendor/jquery", root_dir + "/sdkjs/vendor/jquery")
        base.copy_dir(base_dir + "/js/" + branding + "/builder/web-apps/vendor/xregexp", root_dir + "/sdkjs/vendor/xregexp")

        # ---- C++ 头文件（供二次开发使用） ----
        base.create_dir(root_dir + "/include")
        base.copy_file(core_dir + "/DesktopEditor/doctrenderer/common_deploy.h", root_dir + "/include/common.h")
        base.copy_file(core_dir + "/DesktopEditor/doctrenderer/docbuilder.h", root_dir + "/include/docbuilder.h")
        if (0 == platform.find("win")):
            base.copy_file(core_dir + "/DesktopEditor/doctrenderer/docbuilder.com/src/docbuilder_midl.h", root_dir + "/include/docbuilder_midl.h")
        base.replaceInFile(root_dir + "/include/docbuilder.h", "Q_DECL_EXPORT", "BUILDING_DOCBUILDER")

        # ---- COM 和 .NET 封装 ----
        if ("win_64" == platform):
            base.copy_file(core_dir + "/DesktopEditor/doctrenderer/docbuilder.com/deploy/win_64/docbuilder.com.dll", root_dir + "/docbuilder.com.dll")
            base.copy_file(core_dir + "/DesktopEditor/doctrenderer/docbuilder.net/deploy/win_64/docbuilder.net.dll", root_dir + "/docbuilder.net.dll")
        elif ("win_32" == platform):
            base.copy_file(core_dir + "/DesktopEditor/doctrenderer/docbuilder.com/deploy/win_32/docbuilder.com.dll", root_dir + "/docbuilder.com.dll")
            base.copy_file(core_dir + "/DesktopEditor/doctrenderer/docbuilder.net/deploy/win_32/docbuilder.net.dll", root_dir + "/docbuilder.net.dll")

        # ---- iOS Framework 处理 ----
        if ("ios" == platform):
            base.for_each_framework(root_dir, "ios", callbacks=[base.generate_plist, base.generate_xcprivacy])

        # ---- Linux/macOS RPATH 修正 ----
        if (0 == platform.find("linux")):
            base.linux_correct_rpath_docbuilder(root_dir)
        if (0 == platform.find("mac")):
            base.for_each_framework(root_dir, "mac", callbacks=[base.generate_plist], max_depth=1)
            base.mac_correct_rpath_x2t(root_dir)
            base.mac_correct_rpath_docbuilder(root_dir)

        # ---- 生成 x2t JS 缓存 ----
        base.create_x2t_js_cache(root_dir, "builder", platform)

        # ---- 复制字体 ----
        base.create_dir(root_dir + "/fonts")
        base.copy_dir(git_dir  + "/core-fonts/asana",      root_dir + "/fonts/asana")
        base.copy_dir(git_dir  + "/core-fonts/caladea",    root_dir + "/fonts/caladea")
        base.copy_dir(git_dir  + "/core-fonts/crosextra",  root_dir + "/fonts/crosextra")
        base.copy_dir(git_dir  + "/core-fonts/openoffice", root_dir + "/fonts/openoffice")
        base.copy_file(git_dir + "/core-fonts/ASC.ttf",    root_dir + "/fonts/ASC.ttf")

        # ---- 清理不需要的文件（减小部署包体积） ----
        def delete_files(files):
            for file in files:
                base.delete_file(file)

        delete_files(base.find_files(root_dir, "*.wasm"))
        delete_files(base.find_files(root_dir, "*_ie.js"))
        base.delete_file(root_dir + "/sdkjs/pdf/src/engine/cmap.bin")
        if 0 != platform.find("mac"):
            delete_files(base.find_files(root_dir, "sdk-all.js"))
            delete_files(base.find_files(root_dir, "sdk-all-min.js"))
        base.delete_dir(root_dir + "/sdkjs/slide/themes")
        base.delete_dir(root_dir + "/sdkjs/cell/css")
        base.delete_file(root_dir + "/sdkjs/pdf/src/engine/viewer.js")
        base.delete_file(root_dir + "/sdkjs/common/spell/spell/spell.js.mem")
        base.delete_dir(root_dir + "/sdkjs/common/Images")

    return
