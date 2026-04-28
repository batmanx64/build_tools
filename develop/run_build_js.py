#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_build_js.py - Docker 环境 JS 构建运行脚本
==============================================
功能：在 Docker 容器中执行 JS 构建。更新 supervisor 配置指向正确的
docservice/converter 路径（源码模式或 pkg 二进制模式），并调用 run_server。
"""

import sys
sys.path.append(sys.argv[1] + '/build_tools/scripts')
sys.path.append(sys.argv[1] + '/build_tools/scripts/develop')
import build_js
import run_server
import config
import base

git_dir = sys.argv[1]

base.print_info('argv :'+' '.join(sys.argv))
base.cmd_in_dir(git_dir + '/build_tools/', 'python3', ['configure.py', '--develop', '1'] + sys.argv[2:])

config.parse()
config.parse_defaults()

# 删除字体缓存，以便在有外部 SDKJS 卷时重新生成字体
if base.is_exist(git_dir + "/server/FileConverter/bin/fonts.log"):
    base.print_info('remove font cache to regenerate fonts in external sdkjs volume')
    base.delete_file(git_dir + "/server/FileConverter/bin/fonts.log")

# ---- 外部 Server 卷模式：使用 Node.js 源码运行 ----
if base.is_exist(sys.argv[1] + '/server/DocService/package.json'):
    base.print_info('replace supervisor cfg to run docservice and converter from source')
    base.replaceInFileRE("/etc/supervisor/conf.d/ds-docservice.conf", "command=.*", "command=node " + git_dir + "/server/DocService/sources/server.js")
    base.replaceInFileRE("/app/ds/setup/config/supervisor/ds/ds-docservice.conf", "command=.*", "command=node " + git_dir + "/server/DocService/sources/server.js")
    base.replaceInFileRE("/etc/supervisor/conf.d/ds-converter.conf", "command=.*", "command=node " + git_dir + "/server/FileConverter/sources/convertermaster.js")
    base.replaceInFileRE("/app/ds/setup/config/supervisor/ds/ds-converter.conf", "command=.*", "command=node " + git_dir + "/server/FileConverter/sources/convertermaster.js")
    base.print_info('run_server.run_docker_server')
    run_server.run_docker_server()
else:
    # ---- 外部 SDKJS 卷模式：修正 DoctRenderer 配置 ----
    if base.is_exist(git_dir + "/server/FileConverter/bin/DoctRenderer.config"):
        base.print_info('replace DoctRenderer.config for external sdkjs volume')
        base.generate_doctrenderer_config(git_dir + "/server/FileConverter/bin/DoctRenderer.config", "../../../sdkjs/deploy/", "server", "../../../web-apps/vendor/", "../../../dictionaries")

    # ---- 添加 SDKJS 和 WebApps 插件的静态内容配置 ----
    addons = {}
    addons.update(base.get_sdkjs_addons())
    addons.update(base.get_web_apps_addons())
    staticContent = ""
    for addon in addons:
        if (addon):
            staticContent += '"/' + addon + '": {"path": "/var/www/onlyoffice/documentserver/' + addon + '","options": {"maxAge": "7d"}},'

    if staticContent:
        base.print_info('replace production-linux.json for addons'+staticContent)
        base.replaceInFileRE("/etc/onlyoffice/documentserver/production-linux.json", '"static_content": {.*', '"static_content": {' + staticContent)

    # ---- pkg 二进制模式：更新 supervisor 配置 ----
    base.print_info('replace supervisor cfg to run docservice and converter from pkg')
    base.replaceInFileRE("/etc/supervisor/conf.d/ds-docservice.conf", "command=node .*", "command=/var/www/onlyoffice/documentserver/server/DocService/docservice")
    base.replaceInFileRE("/app/ds/setup/config/supervisor/ds/ds-docservice.conf", "command=node .*", "command=/var/www/onlyoffice/documentserver/server/DocService/docservice")
    base.replaceInFileRE("/etc/supervisor/conf.d/ds-converter.conf", "command=node .*", "command=/var/www/onlyoffice/documentserver/server/FileConverter/converter")
    base.replaceInFileRE("/app/ds/setup/config/supervisor/ds/ds-converter.conf", "command=node .*", "command=/var/www/onlyoffice/documentserver/server/FileConverter/converter")
    base.print_info('run_server.run_docker_sdk_web_apps: ' + git_dir)
    run_server.run_docker_sdk_web_apps(git_dir)
