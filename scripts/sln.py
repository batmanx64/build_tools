#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
sln.py - 解决方案项目列表解析模块
===================================
功能：解析 sln.json 文件，根据 --module 和 --platform 参数筛选出需要编译的 .pro 文件列表。
支持条件编译过滤：
  - 平台过滤：[win], [linux], [mac], [android], [win_64], [!no_x2t] 等
  - 配置过滤：[!debug], [!no_tests] 等
  - 平台别名：win = win_64 win_32 ..., linux = linux_64 linux_32 ...
"""

import sys
sys.path.append('scripts')
import config
import json
import os

is_log = False


def is_exist_in_array(projects, proj):
    """检查项目是否已存在于列表中（避免重复）。"""
    for p in projects:
        if p == proj:
            return True
    return False


def get_full_projects_list(json_data, list):
    """
    递归展开项目列表。
    如果列表中的项是 sln.json 中的键（模块名），则递归展开该键对应的子列表。
    """
    result = []
    for rec in list:
        if rec in json_data:
            result += get_full_projects_list(json_data, json_data[rec])
        else:
            result.append(rec)
    return result


def adjust_project_params(params):
    """
    展开平台别名过滤器。
    例如：[win] → [win_64 win_32 win_64_xp win_32_xp win_arm64]
           [!win] → [!win_64 !win_32 ...]
    """
    ret_params = params

    all_windows = []
    all_windows_xp = []
    all_linux = []
    all_mac = []
    all_android = []

    for i in config.platforms:
        if (0 == i.find("win")):
            all_windows.append(i)
            if (-1 != i.find("xp")):
                all_windows_xp.append(i)
        elif (0 == i.find("linux")):
            all_linux.append(i)
        elif (0 == i.find("mac")):
            all_mac.append(i)
        elif (0 == i.find("android")):
            all_android.append(i)

    if is_exist_in_array(params, "win"):
        ret_params += all_windows
    if is_exist_in_array(params, "!win"):
        ret_params += ["!" + x for x in all_windows]

    if is_exist_in_array(params, "win_xp"):
        ret_params += all_windows_xp
    if is_exist_in_array(params, "!win_xp"):
        ret_params += ["!" + x for x in all_windows_xp]

    if is_exist_in_array(params, "linux"):
        ret_params += all_linux
    if is_exist_in_array(params, "!linux"):
        ret_params += ["!" + x for x in all_linux]

    if is_exist_in_array(params, "mac"):
        ret_params += all_mac
    if is_exist_in_array(params, "!mac"):
        ret_params += ["!" + x for x in all_mac]

    if is_exist_in_array(params, "android"):
        ret_params += all_android
    if is_exist_in_array(params, "!android"):
        ret_params += ["!" + x for x in all_android]

    return ret_params


def get_projects(pro_json_path, platform):
    """
    主函数：获取指定平台需要编译的 .pro 文件列表。

    过滤逻辑：
    1. 读取 sln.json，获取 --module 对应的项目列表
    2. 递归展开模块引用
    3. 解析每条记录的 [platform_filter] 前缀
    4. 根据当前平台和 config 选项过滤

    过滤语法示例：
      "[win,linux,mac]core/xxx.pro"    — 在 win/linux/mac 上编译
      "[!no_x2t]core/OOXML/xxx.pro"    — 当 config 中没有 no_x2t 时编译
      "[!no_tests]core/Test/xxx.pro"   — 当 config 中没有 no_tests 时编译
      "[win,linux,mac,!linux_arm64]..."— 不在 linux_arm64 上编译
    """
    json_path = os.path.abspath(pro_json_path)
    data = json.load(open(json_path))

    root_dir_json = "../"
    if ("root" in data):
        root_dir_json = data["root"]

    root_dir = os.path.dirname(json_path)
    if ("/" != root_dir[-1] and "\\" != root_dir[-1]):
        root_dir += "/"
    root_dir += root_dir_json

    result = []
    modules = config.option("module").split(" ")
    for module in modules:
        if (module == ""):
            continue
        if not module in data:
            continue

        records_src = data[module]
        records = get_full_projects_list(data, records_src)

        for rec in records:
            params = []
            record = rec
            # 解析 [platform_filter] 前缀
            if (0 == rec.find("[")):
                pos = rec.find("]")
                if (-1 == pos):
                    continue
                record = rec[pos+1:]
                header = rec[1:pos].replace(" ", "")
                params_tmp = rec[1:pos].split(",")
                for par in params_tmp:
                    if (par != ""):
                        params.append(par)

                params = adjust_project_params(params)

            if is_exist_in_array(result, record):
                continue

            if is_log:
                print("params: " + ",".join(params))
                print("file: " + record)

            # [!platform] = 排除此平台
            if is_exist_in_array(params, "!" + platform):
                continue

            platform_records = []
            platform_records += config.platforms
            platform_records += ["win", "win_xp", "linux", "mac", "android"]

            # 检查是否指定了至少一个目标平台
            is_needed_platform_exist = False
            for pl in platform_records:
                if is_exist_in_array(params, pl):
                    is_needed_platform_exist = True
                    break

            # 检查是否指定了至少一个 config 条件
            is_needed_config_exist = False
            for item in params:
                if (0 == item.find("!")):
                    continue
                if is_exist_in_array(platform_records, item):
                    continue
                is_needed_config_exist = True
                break

            if is_needed_platform_exist:
                if not is_exist_in_array(params, platform):
                    continue

            # 检查 config 条件是否满足
            config_params = config.option("config").split(" ") + config.option("features").split(" ")
            config_params = [x for x in config_params if x]

            is_append = True
            for conf in config_params:
                if is_exist_in_array(params, "!" + conf):
                    is_append = False
                    break
                if is_needed_config_exist and not is_exist_in_array(params, conf):
                    is_append = False
                    break
            if is_append:
                result.append(root_dir + record)

    # 去重（保留首次出现的顺序）
    old_results = result
    result = []

    map_results = set()
    for item in old_results:
        proj = item.replace("\\", "/")
        if proj in map_results:
            continue
        map_results.add(proj)
        result.append(proj)

    if is_log:
        print(result)
    return result


if __name__ == '__main__':
    # 测试入口
    config.parse()
    is_log = True
    projects = get_projects("./../sln.json", "win_64")
