#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
deploy_server.py - Server 部署脚本
===================================
功能：将 Server 的构建产物按平台部署到 out/<platform>/<branding>/documentserver/ 目录。
覆盖多个微服务（DocService、FileConverter、Metrics、AdminPanel）以及插件、字体、配置等。
支持 snap 包格式的额外部署。
"""

import config
import base

import re
import shutil
import glob
from tempfile import mkstemp

def make():
    """主入口：遍历目标平台，执行 Server 部署。"""
    base_dir = base.get_script_dir() + "/../out"
    git_dir = base.get_script_dir() + "/../.."
    core_dir = git_dir + "/core"
    plugins_dir = git_dir + "/sdkjs-plugins"
    branding = config.branding()

    platforms = config.option("platform").split()
    for native_platform in platforms:
        if not native_platform in config.platforms:
            continue

        # 跳过不支持的平台（xp、ios、android）
        if (-1 != native_platform.find("_xp")):
            print("Server module not supported on Windows XP")
            continue

        if (-1 != native_platform.find("ios")):
            print("Server module not supported on iOS")
            continue

        if (-1 != native_platform.find("android")):
            print("Server module not supported on Android")
            continue

        # ---- 创建输出目录 ----
        root_dir = base_dir + ("/" + native_platform + "/" + branding + "/documentserver")
        root_dir_snap = root_dir + '-snap/var/www/onlyoffice/documentserver'
        root_dir_snap_example = root_dir_snap + '-example'
        if (base.is_dir(root_dir)):
            base.delete_dir(root_dir)
        base.create_dir(root_dir)

        build_server_dir = root_dir + '/server'
        server_dir = base.get_script_dir() + "/../../server"
        server_admin_panel_dir = base.get_script_dir() + "/../../server-admin-panel"

        # ---- 复制 Common 配置 ----
        base.create_dir(build_server_dir + '/DocService')
        base.copy_dir(server_dir + '/Common/config', build_server_dir + '/Common/config')

        # ---- 复制 DocService（文档协同服务） ----
        base.create_dir(build_server_dir + '/DocService')
        base.copy_exe(server_dir + "/DocService", build_server_dir + '/DocService', "docservice")

        # ---- 复制 FileConverter（文件转换服务） ----
        base.create_dir(build_server_dir + '/FileConverter')
        base.copy_exe(server_dir + "/FileConverter", build_server_dir + '/FileConverter', "converter")

        # ---- 复制 Metrics（监控指标服务） ----
        base.create_dir(build_server_dir + '/Metrics')
        base.copy_exe(server_dir + "/Metrics", build_server_dir + '/Metrics', "metrics")
        base.copy_dir(server_dir + '/Metrics/config', build_server_dir + '/Metrics/config')
        base.create_dir(build_server_dir + '/Metrics/node_modules/modern-syslog/build/Release')
        base.copy_file(server_dir + "/Metrics/node_modules/modern-syslog/build/Release/core.node", build_server_dir + "/Metrics/node_modules/modern-syslog/build/Release/core.node")

        # ---- 复制 AdminPanel（管理面板，可选） ----
        if "server-admin-panel" in base.get_server_addons() and base.is_exist(server_admin_panel_dir):
            # AdminPanel 服务端部分
            base.create_dir(build_server_dir + '/AdminPanel/server')
            base.copy_exe(server_admin_panel_dir + "/server", build_server_dir + '/AdminPanel/server', "adminpanel")

            # AdminPanel 客户端部分（React 构建产物）
            base.create_dir(build_server_dir + '/AdminPanel/client/build')
            base.copy_dir(server_admin_panel_dir + '/client/build', build_server_dir + '/AdminPanel/client/build')

        # ---- 复制 Core 编译产物到 FileConverter/bin ----
        qt_dir = base.qt_setup(native_platform)
        platform = native_platform

        core_build_dir = core_dir + "/build"
        if ("" != config.option("branding")):
            core_build_dir += ("/" + config.option("branding"))

        platform_postfix = platform + base.qt_dst_postfix()

        converter_dir = root_dir + "/server/FileConverter/bin"
        base.create_dir(converter_dir)

        # 复制所有 Core 动态库（格式处理引擎、渲染器等）
        base.copy_lib(core_build_dir + "/lib/" + platform_postfix, converter_dir, "kernel")
        base.copy_lib(core_build_dir + "/lib/" + platform_postfix, converter_dir, "kernel_network")
        base.copy_lib(core_build_dir + "/lib/" + platform_postfix, converter_dir, "UnicodeConverter")
        base.copy_lib(core_build_dir + "/lib/" + platform_postfix, converter_dir, "graphics")
        base.copy_lib(core_build_dir + "/lib/" + platform_postfix, converter_dir, "PdfFile")
        base.copy_lib(core_build_dir + "/lib/" + platform_postfix, converter_dir, "DjVuFile")
        base.copy_lib(core_build_dir + "/lib/" + platform_postfix, converter_dir, "XpsFile")
        base.copy_lib(core_build_dir + "/lib/" + platform_postfix, converter_dir, "OFDFile")
        base.copy_lib(core_build_dir + "/lib/" + platform_postfix, converter_dir, "HtmlFile2")
        base.copy_lib(core_build_dir + "/lib/" + platform_postfix, converter_dir, "doctrenderer")
        base.copy_lib(core_build_dir + "/lib/" + platform_postfix, converter_dir, "Fb2File")
        base.copy_lib(core_build_dir + "/lib/" + platform_postfix, converter_dir, "EpubFile")
        base.copy_lib(core_build_dir + "/lib/" + platform_postfix, converter_dir, "IWorkFile")
        base.copy_lib(core_build_dir + "/lib/" + platform_postfix, converter_dir, "HWPFile")
        base.copy_lib(core_build_dir + "/lib/" + platform_postfix, converter_dir, "DocxRenderer")
        base.copy_lib(core_build_dir + "/lib/" + platform_postfix, converter_dir, "StarMathConverter")
        base.copy_lib(core_build_dir + "/lib/" + platform_postfix, converter_dir, "ooxmlsignature")
        # cmap.bin：PDF 字符映射表
        base.copy_file(git_dir + "/sdkjs/pdf/src/engine/cmap.bin", converter_dir + "/cmap.bin")
        # x2t：文档格式转换引擎
        base.copy_exe(core_build_dir + "/bin/" + platform_postfix, converter_dir, "x2t")

        # ---- 生成 DoctRenderer 配置 ----
        base.generate_doctrenderer_config(converter_dir + "/DoctRenderer.config", "../../../", "server", "", "../../../dictionaries")

        # ---- 部署 ICU 国际化数据和 V8 引擎文件 ----
        base.deploy_icu(core_dir, converter_dir, platform)
        base.copy_v8_files(core_dir, converter_dir, platform)

        # ---- 复制 docbuilder（文档生成器） ----
        base.copy_exe(core_build_dir + "/bin/" + platform_postfix, converter_dir, "docbuilder")
        base.copy_dir(git_dir + "/document-templates/new/en-US", converter_dir + "/empty")

        # ---- macOS 平台修正 Framework 路径 ----
        if (0 == platform.find("mac")):
            base.for_each_framework(converter_dir, "mac", callbacks=[base.generate_plist], max_depth=1)

        # ---- 部署 JS 资源（sdkjs + web-apps） ----
        js_dir = root_dir
        base.copy_dir(base_dir + "/js/" + branding + "/builder/sdkjs", js_dir + "/sdkjs")
        base.copy_dir(base_dir + "/js/" + branding + "/builder/web-apps", js_dir + "/web-apps")
        # 删除 .js.map 调试文件（生产环境不需要）
        for file in glob.glob(js_dir + "/web-apps/apps/*/*/*.js.map") \
                  + glob.glob(js_dir + "/web-apps/apps/*/mobile/dist/js/*.js.map"):
            base.delete_file(file)

        # ---- 生成 x2t JS 缓存 ----
        base.create_x2t_js_cache(converter_dir, "server", platform)

        # ---- 嵌入 worker 代码 ----
        base.cmd_in_dir(git_dir + "/sdkjs/common/embed", "python", ["make.py", js_dir + "/web-apps/apps/api/documents/api.js"])

        # ---- 部署 SDKJS 插件 ----
        base.create_dir(js_dir + "/sdkjs-plugins")
        base.copy_marketplace_plugin(js_dir + "/sdkjs-plugins", False, True)
        if ("1" == config.option("preinstalled-plugins")):
            base.copy_sdkjs_plugins(js_dir + "/sdkjs-plugins", False, True)
            base.copy_sdkjs_plugins_server(js_dir + "/sdkjs-plugins", False, True)
        else:
            base.generate_sdkjs_plugin_list(js_dir + "/sdkjs-plugins/plugin-list-default.json")
        # 下载 v1 版本的官方插件列表
        base.create_dir(js_dir + "/sdkjs-plugins/v1")
        base.download("https://onlyoffice.github.io/sdkjs-plugins/v1/plugins.js", js_dir + "/sdkjs-plugins/v1/plugins.js")
        base.download("https://onlyoffice.github.io/sdkjs-plugins/v1/plugins-ui.js", js_dir + "/sdkjs-plugins/v1/plugins-ui.js")
        base.download("https://onlyoffice.github.io/sdkjs-plugins/v1/plugins.css", js_dir + "/sdkjs-plugins/v1/plugins.css")
        base.support_old_versions_plugins(js_dir + "/sdkjs-plugins")

        # ---- 复制工具（allfontsgen、allthemesgen、pluginsmanager） ----
        tools_dir = root_dir + "/server/tools"
        base.create_dir(tools_dir)
        base.copy_exe(core_build_dir + "/bin/" + platform_postfix, tools_dir, "allfontsgen")
        base.copy_exe(core_build_dir + "/bin/" + platform_postfix, tools_dir, "allthemesgen")
        if ("1" != config.option("preinstalled-plugins")):
            base.copy_exe(core_build_dir + "/bin/" + platform_postfix, tools_dir, "pluginsmanager")

        # ---- 复制 branding 资源 ----
        branding_dir = server_dir + "/branding"
        if("" != config.option("branding") and "onlyoffice" != config.option("branding")):
            branding_dir = git_dir + '/' + config.option("branding") + '/server'

        # ---- 复制字典（拼写检查） ----
        base.copy_dictionaries(server_dir + "/../dictionaries", root_dir + "/dictionaries")

        # ---- 确定可执行文件扩展名 ----
        if (0 == platform.find("win")):
            exec_ext = '.exe'
        else:
            exec_ext = ''

        # ---- 复制 schema（数据库模式定义） ----
        schema_files = server_dir + '/schema'
        schema = build_server_dir + '/schema'
        base.create_dir(schema)
        base.copy_dir(schema_files, schema)

        # ---- 复制 core-fonts（核心字体） ----
        core_fonts_files = server_dir + '/../core-fonts'
        core_fonts = build_server_dir + '/../core-fonts'
        base.create_dir(core_fonts)
        base.copy_dir_content(core_fonts_files, core_fonts, "", ".git")

        # ---- 复制文档模板 ----
        document_templates_files = server_dir + '/../document-templates'
        document_templates = build_server_dir + '/../document-templates'
        base.copy_dir(document_templates_files + '/new', document_templates + '/new')
        base.copy_dir(document_templates_files + '/sample', document_templates + '/sample')

        # ---- 复制文档格式定义 ----
        document_formats_files = server_dir + '/../document-formats'
        document_formats = build_server_dir + '/../document-formats'
        base.create_dir(document_formats)
        base.copy_file(document_formats_files + '/onlyoffice-docs-formats.json', document_formats + '/onlyoffice-docs-formats.json')

        # ---- 复制许可证文件 ----
        license_file1 = server_dir + '/LICENSE.txt'
        license_file2 = server_dir + '/3rd-Party.txt'
        license_dir = server_dir + '/license'
        license = build_server_dir + '/license'
        base.copy_file(license_file1, build_server_dir)
        base.copy_file(license_file2, build_server_dir)
        base.copy_dir(license_dir, license)
        base.copy_dir(server_dir + '/dictionaries', build_server_dir + '/dictionaries')

        # ---- 复制 branding 欢迎页和信息页 ----
        welcome_files = branding_dir + '/welcome'
        welcome = build_server_dir + '/welcome'
        base.create_dir(welcome)
        base.copy_dir(welcome_files, welcome)

        info_files = branding_dir + '/info'
        info = build_server_dir + '/info'
        base.create_dir(info)
        base.copy_dir(info_files, info)

        # ---- 复制 Example（示例程序） ----
        build_example_dir = root_dir + '-example'
        bin_example_dir = base.get_script_dir() + "/../../document-server-integration/web/documentserver-example/nodejs"

        base.create_dir(build_example_dir)
        base.copy_exe(bin_example_dir, build_example_dir, "example")
        base.copy_dir(bin_example_dir + "/config", build_example_dir + "/config")

        # ---- snap 包格式的额外部署（仅 Linux） ----
        # snap 包需要保留 node_modules 源码（pkg 二进制不可用）
        if (0 == platform.find("linux")):
            if (base.is_dir(root_dir_snap)):
                base.delete_dir(root_dir_snap)
            base.create_dir(root_dir_snap)
            base.copy_dir(root_dir, root_dir_snap)
            base.copy_dir(server_dir + '/DocService/node_modules', root_dir_snap + '/server/DocService/node_modules')
            base.copy_dir(server_dir + '/DocService/sources', root_dir_snap + '/server/DocService/sources')
            base.copy_dir(server_dir + '/DocService/public', root_dir_snap + '/server/DocService/public')
            base.delete_file(root_dir_snap + '/server/DocService/docservice')
            base.copy_dir(server_dir + '/FileConverter/node_modules', root_dir_snap + '/server/FileConverter/node_modules')
            base.copy_dir(server_dir + '/FileConverter/sources', root_dir_snap + '/server/FileConverter/sources')
            base.delete_file(root_dir_snap + '/server/FileConverter/converter')
            base.copy_dir(server_dir + '/Common/node_modules', root_dir_snap + '/server/Common/node_modules')
            base.copy_dir(server_dir + '/Common/sources', root_dir_snap + '/server/Common/sources')
            if (base.is_dir(root_dir_snap_example)):
                base.delete_dir(root_dir_snap_example)
            base.create_dir(root_dir_snap_example)
            base.copy_dir(bin_example_dir + '/..', root_dir_snap_example)
            base.delete_file(root_dir_snap + '/example/nodejs/example')

    return
