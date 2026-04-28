#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
deploy_desktop.py - Desktop Editors 部署脚本
==============================================
功能：将 Desktop Editors 的构建产物按平台部署到 out/<platform>/<branding>/desktopeditors 目录。
桌面版需要部署：x2t 转换器、Qt 库、CEF 浏览器引擎、字体、主题、JS 资源、插件等。
"""

import config
import base
import os
import platform
import glob

def copy_lib_with_links(src_dir, dst_dir, lib, version):
    """复制动态库并创建符号链接链（用于 libvlc 部署）。"""
    lib_full_name = lib + "." + version
    major_version = version[:version.find(".")]
    lib_major_name = lib + "." + major_version

    base.copy_file(src_dir + "/" + lib_full_name, dst_dir + "/" + lib_full_name)
    base.cmd_in_dir(dst_dir, "ln", ["-s", "./" + lib_full_name, "./" + lib_major_name])
    base.cmd_in_dir(dst_dir, "ln", ["-s", "./" + lib_major_name, "./" + lib])
    return

def make():
    """主入口：遍历目标平台，执行 Desktop Editors 部署。"""
    base_dir = base.get_script_dir() + "/../out"
    git_dir = base.get_script_dir() + "/../.."
    core_dir = git_dir + "/core"
    branding = config.branding()

    platforms = config.option("platform").split()
    for native_platform in platforms:
        if not native_platform in config.platforms:
            continue

        root_dir = base_dir + ("/" + native_platform + "/" + branding + ("/DesktopEditors" if base.is_windows() else "/desktopeditors"))
        if (base.is_dir(root_dir)):
            base.delete_dir(root_dir)
        base.create_dir(root_dir)

        qt_dir = base.qt_setup(native_platform)

        # ---- 检查是否是 Windows XP 平台 ----
        isWindowsXP = False if (-1 == native_platform.find("_xp")) else True
        platform = native_platform[0:-3] if isWindowsXP else native_platform

        # 构建产物后缀路径
        apps_postfix = "build" + base.qt_dst_postfix()
        if ("" != config.option("branding")):
            apps_postfix += ("/" + config.option("branding"))
        apps_postfix += "/"
        apps_postfix += platform
        if isWindowsXP:
            apps_postfix += "/xp"

        core_build_dir = core_dir + "/build"
        if ("" != config.option("branding")):
            core_build_dir += ("/" + config.option("branding"))

        platform_postfix = platform + base.qt_dst_postfix()
        build_libraries_path = core_build_dir + "/lib/" + platform_postfix

        # ============ 部署 x2t 文档转换器 ============
        base.create_dir(root_dir + "/converter")
        base.copy_lib(build_libraries_path, root_dir + "/converter", "kernel")
        base.copy_lib(build_libraries_path, root_dir + "/converter", "kernel_network")
        base.copy_lib(build_libraries_path, root_dir + "/converter", "UnicodeConverter")
        base.copy_lib(build_libraries_path, root_dir + "/converter", "graphics")
        base.copy_lib(build_libraries_path, root_dir + "/converter", "PdfFile")
        base.copy_lib(build_libraries_path, root_dir + "/converter", "DjVuFile")
        base.copy_lib(build_libraries_path, root_dir + "/converter", "XpsFile")
        base.copy_lib(build_libraries_path, root_dir + "/converter", "OFDFile")
        base.copy_lib(build_libraries_path, root_dir + "/converter", "HtmlFile2")
        base.copy_lib(build_libraries_path, root_dir + "/converter", "Fb2File")
        base.copy_lib(build_libraries_path, root_dir + "/converter", "EpubFile")
        base.copy_lib(build_libraries_path, root_dir + "/converter", "IWorkFile")
        base.copy_lib(build_libraries_path, root_dir + "/converter", "HWPFile")
        base.copy_lib(build_libraries_path, root_dir + "/converter", "DocxRenderer")
        base.copy_lib(build_libraries_path, root_dir + "/converter", "StarMathConverter")
        base.copy_lib(build_libraries_path, root_dir + "/converter", "ooxmlsignature", "xp" if isWindowsXP else "")

        # x2t 可执行文件
        if ("ios" == platform):
            base.copy_lib(build_libraries_path, root_dir + "/converter", "x2t")
        else:
            base.copy_exe(core_build_dir + "/bin/" + platform_postfix, root_dir + "/converter", "x2t")

        # ---- ICU 国际化数据 ----
        base.deploy_icu(core_dir, root_dir + "/converter", native_platform)

        # ---- doctrenderer（文档渲染器） ----
        if isWindowsXP:
            base.copy_lib(build_libraries_path + "/xp", root_dir + "/converter", "doctrenderer")
        else:
            base.copy_lib(build_libraries_path, root_dir + "/converter", "doctrenderer")
        base.copy_v8_files(core_dir, root_dir + "/converter", platform, isWindowsXP)

        # ---- 生成渲染器配置 ----
        base.generate_doctrenderer_config(root_dir + "/converter/DoctRenderer.config", "../editors/", "desktop", "", "../dictionaries")
        base.copy_dir(git_dir + "/document-templates/new", root_dir + "/converter/empty")
        base.copy_dir(git_dir + "/desktop-apps/common/templates", root_dir + "/converter/templates")

        # ---- 字典（拼写检查） ----
        base.copy_dictionaries(git_dir + "/dictionaries", root_dir + "/dictionaries")

        # ---- 字体 ----
        base.copy_dir(git_dir  + "/core-fonts/opensans",   root_dir + "/fonts")
        base.copy_dir(git_dir  + "/core-fonts/asana",      root_dir + "/fonts/asana")
        base.copy_dir(git_dir  + "/core-fonts/caladea",    root_dir + "/fonts/caladea")
        base.copy_dir(git_dir  + "/core-fonts/crosextra",  root_dir + "/fonts/crosextra")
        base.copy_dir(git_dir  + "/core-fonts/openoffice", root_dir + "/fonts/openoffice")
        base.copy_file(git_dir + "/core-fonts/ASC.ttf",    root_dir + "/fonts/ASC.ttf")

        # ============ CEF（Chromium Embedded Framework）浏览器引擎 ============
        build_dir_name = "build"
        if (0 == platform.find("linux")) and (config.check_option("config", "cef_version_107")):
            build_dir_name = "build_107"
        elif (0 == platform.find("mac")) and (config.check_option("config", "use_v8")):
            build_dir_name = "build_103"

        if not isWindowsXP:
            base.copy_files(core_dir + "/Common/3dParty/cef/" + platform + "/" + build_dir_name + "/*", root_dir)
        else:
            base.copy_files(core_dir + "/Common/3dParty/cef/" + native_platform + "/" + build_dir_name + "/*", root_dir)

        # ---- macOS 上修正 CEF Framework 目录结构 ----
        # CEF 下载的 Framework 是扁平结构，需要调整为 Apple 标准的 Versions/A 结构
        if (0 == platform.find("mac")):
            dir_base_old = os.getcwd()
            os.chdir(root_dir + "/Chromium Embedded Framework.framework")
            base.create_dir("Versions")
            base.create_dir("Versions/A")
            base.move_file("Chromium Embedded Framework", "Versions/A/Chromium Embedded Framework")
            base.move_dir("Resources", "Versions/A/Resources")
            base.move_dir("Libraries", "Versions/A/Libraries")
            base.cmd("ln", ["-s", "Versions/A/Chromium Embedded Framework", "Chromium Embedded Framework"])
            base.cmd("ln", ["-s", "Versions/A/Resources", "Resources"])
            base.cmd("ln", ["-s", "Versions/A/Libraries", "Libraries"])
            base.cmd("ln", ["-s", "A", "Versions/Current"])
            os.chdir(dir_base_old);

        # ============ Qt 库和插件部署 ============
        isUseQt = True
        if (0 == platform.find("mac")) or (0 == platform.find("ios")):
            isUseQt = False  # macOS/iOS 使用原生框架而非 Qt

        # ---- 桌面版核心库 ----
        base.copy_lib(build_libraries_path, root_dir, "hunspell")
        base.copy_lib(build_libraries_path + ("/xp" if isWindowsXP else ""), root_dir, "ascdocumentscore")
        if (0 != platform.find("mac")):
            base.copy_lib(build_libraries_path + ("/xp" if isWindowsXP else ""), root_dir, "qtascdocumentscore")

        # ---- editors_helper（渲染辅助进程） ----
        if (0 == platform.find("mac")):
            base.copy_dir(core_build_dir + "/bin/" + platform_postfix + "/editors_helper.app", root_dir + "/editors_helper.app")
        else:
            base.copy_exe(core_build_dir + "/bin/" + platform_postfix + ("/xp" if isWindowsXP else ""), root_dir, "editors_helper")

        # ---- Qt 运行时的动态库和插件 ----
        if isUseQt:
            base.qt_copy_lib("Qt5Core", root_dir)
            base.qt_copy_lib("Qt5Gui", root_dir)
            base.qt_copy_lib("Qt5PrintSupport", root_dir)
            base.qt_copy_lib("Qt5Svg", root_dir)
            base.qt_copy_lib("Qt5Widgets", root_dir)
            base.qt_copy_lib("Qt5Network", root_dir)
            base.qt_copy_lib("Qt5OpenGL", root_dir)

            base.qt_copy_plugin("bearer", root_dir)
            base.qt_copy_plugin("iconengines", root_dir)
            base.qt_copy_plugin("imageformats", root_dir)
            base.qt_copy_plugin("platforms", root_dir)
            base.qt_copy_plugin("platforminputcontexts", root_dir)
            base.qt_copy_plugin("printsupport", root_dir)
            base.qt_copy_plugin("platformthemes", root_dir)
            base.qt_copy_plugin("xcbglintegrations", root_dir)

            # VLC 播放器不可用时使用 Qt Multimedia 作为备选
            if not base.check_congig_option_with_platfom(platform, "libvlc"):
                base.qt_copy_lib("Qt5Multimedia", root_dir)
                base.qt_copy_lib("Qt5MultimediaWidgets", root_dir)
                base.qt_copy_plugin("mediaservice", root_dir)
                base.qt_copy_plugin("playlistformats", root_dir)

            base.qt_copy_plugin("styles", root_dir)

            # Linux 额外 Qt 库
            if (0 == platform.find("linux")):
                base.qt_copy_lib("Qt5DBus", root_dir)
                base.qt_copy_lib("Qt5X11Extras", root_dir)
                base.qt_copy_lib("Qt5XcbQpa", root_dir)
                base.qt_copy_icu(root_dir, platform)
                if not base.check_congig_option_with_platfom(platform, "libvlc"):
                    base.copy_files(base.get_env("QT_DEPLOY") + "/../lib/libqgsttools_p.so*", root_dir)

            # Windows 平台：复制可执行文件和图标
            if (0 == platform.find("win")):
                base.copy_file(git_dir + "/desktop-apps/win-linux/extras/projicons/" + apps_postfix + "/projicons.exe", root_dir + "/DesktopEditors.exe")
                if not isWindowsXP:
                    base.copy_file(git_dir + "/desktop-apps/win-linux/extras/update-daemon/" + apps_postfix + "/updatesvc.exe", root_dir + "/updatesvc.exe")
                base.copy_file(git_dir + "/desktop-apps/win-linux/" + apps_postfix + "/DesktopEditors.exe", root_dir + "/editors.exe")
                base.copy_file(git_dir + "/desktop-apps/win-linux/res/icons/desktopeditors.ico", root_dir + "/app.ico")
            elif (0 == platform.find("linux")):
                base.copy_file(git_dir + "/desktop-apps/win-linux/" + apps_postfix + "/DesktopEditors", root_dir + "/DesktopEditors")

            # ---- VLC 视频播放器集成（可选） ----
            if base.check_congig_option_with_platfom(platform, "libvlc"):
                vlc_dir = git_dir + "/core/Common/3dParty/libvlc/build/" + platform + "/lib"
                if (0 == platform.find("win")):
                    base.copy_dir(vlc_dir + "/plugins", root_dir + "/plugins")
                    base.copy_files(vlc_dir + "/*.dll", root_dir)
                    base.copy_file(vlc_dir + "/vlc-cache-gen.exe", root_dir + "/vlc-cache-gen.exe")
                elif (0 == platform.find("linux")):
                    base.copy_dir(vlc_dir + "/vlc/plugins", root_dir + "/plugins")
                    base.copy_file(vlc_dir + "/vlc/libcompat.a", root_dir + "/libcompat.a")
                    copy_lib_with_links(vlc_dir + "/vlc", root_dir, "libvlc_pulse.so", "0.0.0")
                    copy_lib_with_links(vlc_dir + "/vlc", root_dir, "libvlc_vdpau.so", "0.0.0")
                    copy_lib_with_links(vlc_dir + "/vlc", root_dir, "libvlc_xcb_events.so", "0.0.0")
                    copy_lib_with_links(vlc_dir, root_dir, "libvlc.so", "5.6.1")
                    copy_lib_with_links(vlc_dir, root_dir, "libvlccore.so", "9.0.1")
                    base.copy_file(vlc_dir + "/vlc/vlc-cache-gen", root_dir + "/vlc-cache-gen")

                # VLC 视频播放器核心库
                if isWindowsXP:
                    base.copy_lib(build_libraries_path + "/mediaplayer/xp", root_dir, "videoplayer")
                else:
                    base.copy_lib(build_libraries_path + "/mediaplayer", root_dir, "videoplayer")
            else:
                base.copy_lib(build_libraries_path + ("/xp" if isWindowsXP else ""), root_dir, "videoplayer")

        # ============ JS 前端资源 ============
        base.create_dir(root_dir + "/editors")
        base.copy_dir(base_dir + "/js/" + branding + "/desktop/sdkjs", root_dir + "/editors/sdkjs")
        base.copy_dir(base_dir + "/js/" + branding + "/desktop/web-apps", root_dir + "/editors/web-apps")
        for file in glob.glob(root_dir + "/editors/web-apps/apps/*/*/*.js.map"):
            base.delete_file(file)
        base.copy_dir(git_dir + "/desktop-sdk/ChromiumBasedEditors/resources/local", root_dir + "/editors/sdkjs/common/Images/local")

        # ============ SDKJS 插件 ============
        base.create_dir(root_dir + "/editors/sdkjs-plugins")
        if not isWindowsXP:
            base.copy_marketplace_plugin(root_dir + "/editors/sdkjs-plugins", True, True, True)
        base.copy_sdkjs_plugins(root_dir + "/editors/sdkjs-plugins", True, True, isWindowsXP)
        # 删除语音识别插件
        if base.is_dir(root_dir + "/editors/sdkjs-plugins/speech"):
            base.delete_dir(root_dir + "/editors/sdkjs-plugins/speech")

        # ---- 下载 v1 插件列表 ----
        base.create_dir(root_dir + "/editors/sdkjs-plugins/v1")
        base.download("https://onlyoffice.github.io/sdkjs-plugins/v1/plugins.js", root_dir + "/editors/sdkjs-plugins/v1/plugins.js")
        base.download("https://onlyoffice.github.io/sdkjs-plugins/v1/plugins-ui.js", root_dir + "/editors/sdkjs-plugins/v1/plugins-ui.js")
        base.download("https://onlyoffice.github.io/sdkjs-plugins/v1/plugins.css", root_dir + "/editors/sdkjs-plugins/v1/plugins.css")
        base.support_old_versions_plugins(root_dir + "/editors/sdkjs-plugins")

        # ---- 内置插件（加密、发送） ----
        base.copy_sdkjs_plugin(git_dir + "/desktop-sdk/ChromiumBasedEditors/plugins/encrypt", root_dir + "/editors/sdkjs-plugins", "advanced2", True)
        base.copy_sdkjs_plugin(git_dir + "/desktop-sdk/ChromiumBasedEditors/plugins", root_dir + "/editors/sdkjs-plugins", "sendto", True)

        # ---- AI Agent 插件（可选） ----
        isUseAgent = True
        if isWindowsXP:
            isUseAgent = False
        if (0 == platform.find("mac")) and (config.check_option("config", "use_v8")):
            isUseAgent = False
        if (isUseAgent):
            agent_plugin_dir = git_dir + "/desktop-sdk/ChromiumBasedEditors/plugins/ai-agent"
            if (False):
                base.cmd_in_dir(agent_plugin_dir, "npm", ["install"], True)
                base.cmd_in_dir(agent_plugin_dir, "npm", ["run", "build"], True)
                base.copy_dir(agent_plugin_dir + "/{9DC93CDB-B576-4F0C-B55E-FCC9C48DD777}", root_dir + "/editors/sdkjs-plugins/{9DC93CDB-B576-4F0C-B55E-FCC9C48DD777}")
            else:
                base.copy_dir(agent_plugin_dir + "/deploy/{9DC93CDB-B576-4F0C-B55E-FCC9C48DD777}", root_dir + "/editors/sdkjs-plugins/{9DC93CDB-B576-4F0C-B55E-FCC9C48DD777}")

        # ---- 入口页面和离线页面 ----
        base.copy_file(base_dir + "/js/" + branding + "/desktop/index.html", root_dir + "/index.html")
        base.create_dir(root_dir + "/editors/webext")
        base.copy_file(base_dir + "/js/" + branding + "/desktop/noconnect.html", root_dir + "/editors/webext/noconnect.html")

        # ---- OAuth 登录页 ----
        if isWindowsXP:
            base.create_dir(root_dir + "/providers")
            base.copy_dir(git_dir + "/desktop-apps/common/loginpage/providers/onlyoffice", root_dir + "/providers/onlyoffice")
        else:
            base.copy_dir(git_dir + "/desktop-apps/common/loginpage/providers", root_dir + "/providers")

        # ============ JSC（JavaScriptCore）检测 ============
        # macOS 上如果 doctrenderer 小于 5MB，说明是 JSC 版本（无 V8），需要移除 icudtl.dat
        isUseJSC = False
        if (0 == platform.find("mac")):
            doctrenderer_lib = "libdoctrenderer.dylib"
            if config.check_option("config", "bundle_dylibs"):
                doctrenderer_lib = "doctrenderer.framework/doctrenderer"
            file_size_doctrenderer = os.path.getsize(root_dir + "/converter/" + doctrenderer_lib)
            print("file_size_doctrenderer: " + str(file_size_doctrenderer))
            if (file_size_doctrenderer < 5*1024*1024):
                isUseJSC = True

        if isUseJSC:
            base.delete_file(root_dir + "/converter/icudtl.dat")

        # ---- 生成 x2t JS 缓存 ----
        base.create_x2t_js_cache(root_dir + "/converter", "desktop", platform)

        # ---- 清理 Windows 上 CEF 附带的 lib 文件 ----
        if (0 == platform.find("win")):
            base.delete_file(root_dir + "/cef_sandbox.lib")
            base.delete_file(root_dir + "/libcef.lib")

        # ============ 字体和主题生成 ============
        is_host_not_arm = False
        host_platform = ""

        # macOS ARM64 上如果主机不是 ARM 架构（通过 QEMU 运行），需要特殊处理
        if (platform == "mac_arm64") and not base.is_os_arm():
            is_host_not_arm = True
            host_platform = "mac_64"

        # ---- 复制字体生成和主题生成工具 ----
        base.copy_exe(core_build_dir + "/bin/" + platform_postfix, root_dir + "/converter", "allfontsgen")
        base.copy_exe(core_build_dir + "/bin/" + platform_postfix, root_dir + "/converter", "allthemesgen")

        # ---- macOS Framework 处理 ----
        if (0 == platform.find("mac")):
            base.for_each_framework(root_dir, "mac", callbacks=[base.generate_plist], max_depth=2)
            base.mac_correct_rpath_desktop(root_dir)

        # ---- 生成 allfonts 和 allthemes 数据 ----
        if is_host_not_arm:
            # 非 ARM 主机上构建 ARM64：从 x86_64 构建目录复制 SDKJS
            sdkjs_dir = root_dir + "/editors/sdkjs"
            str1 = "/" + platform + "/"
            str2 = "/" + host_platform + "/"
            sdkjs_dir_host = sdkjs_dir.replace(str1, str2)
            base.delete_dir(sdkjs_dir)
            base.copy_dir(sdkjs_dir_host, sdkjs_dir)
        else:
            themes_params = []
            if ("" != config.option("themesparams")):
                themes_params = ["--params=\"" + config.option("themesparams") + "\""]

            params_allfontsgen = ["--use-system=\"1\"", "--input=\"" + root_dir + "/fonts\"", "--input=\"" + git_dir + "/core-fonts\"", "--allfonts=\"" + root_dir + "/converter/AllFonts.js\"", "--selection=\"" + root_dir + "/converter/font_selection.bin\""]
            params_allthemesgen = ["--converter-dir=\"" + root_dir + "/converter\"", "--src=\"" + root_dir + "/editors/sdkjs/slide/themes\"", "--allfonts=\"AllFonts.js\"", "--output=\"" + root_dir + "/editors/sdkjs/common/Images\""] + themes_params

            # 交叉编译：ARM Linux 在 x86_64 主机上通过 QEMU 运行
            if (0 == platform.find("linux_arm") and not base.is_os_arm()):
                x2t_origin = ""
                if (config.option("sysroot") != ""):
                    x2t_origin = base.create_qemu_wrapper(root_dir + "/converter/x2t", platform)
                base.cmd_in_dir_qemu(platform, root_dir + "/converter", "./allfontsgen", params_allfontsgen, True)
                base.cmd_in_dir_qemu(platform, root_dir + "/converter", "./allthemesgen", params_allthemesgen, True)
                if "" != x2t_origin:
                    base.delete_file(root_dir + "/converter/x2t")
                    base.move_file(x2t_origin, root_dir + "/converter/x2t")
            else:
                base.cmd_exe(root_dir + "/converter/allfontsgen", params_allfontsgen, True)
                base.cmd_exe(root_dir + "/converter/allthemesgen", params_allthemesgen, True)

            # ---- 清理字体生成产生的临时文件 ----
            base.delete_file(root_dir + "/converter/AllFonts.js")
            base.delete_file(root_dir + "/converter/font_selection.bin")
            base.delete_file(root_dir + "/converter/fonts.log")

        # ---- 如果不是 QEMU 交叉编译，删除字体工具 ----
        if not base.is_use_create_artifacts_qemu(platform):
            base.delete_exe(root_dir + "/converter/allfontsgen")
            base.delete_exe(root_dir + "/converter/allthemesgen")

        # ---- 非 JSC 版本删除缓存文件 ----
        if not isUseJSC:
            base.delete_file(root_dir + "/editors/sdkjs/slide/sdk-all.cache")

    return
