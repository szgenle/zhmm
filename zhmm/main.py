#!/usr/bin/env python3
# coding=utf-8
# @Date: 2024-06-30
# @LastEditTime: 2024-07-02
import os
import sys
import argparse
import getpass

# 获取当前脚本的绝对路径，并推导出项目根目录（假设项目根目录是包含 `project` 的目录）
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)  # 向上回退两级到项目根目录
sys.path.append(project_root)  # 将项目根目录添加到模块搜索路径
sys.path.append(current_dir)  # 将项目根目录添加到模块搜索路径

from gl_ui import ClUI

def main():
    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('--input', '-i', type=str, help='要加载的加密文件路径')
    parser.add_argument('--out', '-o', type=str, help='输出的文件路径')
    parser.add_argument('--openId', type=str, help='微信小程序中显示的OpenId')
    parser.add_argument('--pwd', type=str, help='密码，不设置将在随后提醒输入')
    parser.add_argument('--search', '-s', type=str, help='搜索')
    parser.add_argument('--find', '-f', action='store_true', help='查找')
    parser.add_argument('--new', '-n', action='store_true', help='增加')
    parser.add_argument('--modify', '-m', action='store_true', help='修改')

    user_input_args = parser.parse_args()
    gl_ui = ClUI(user_input_args)

    if not user_input_args.openId:
        print('openId 不能为空')
        return

    file_path = 'zhmm.gl'
    if user_input_args.input:
        file_path = user_input_args.input
    else:
        user_input_args.input = file_path

    if user_input_args.pwd:
        gl_ui.run(file_path, user_input_args.openId, user_input_args.pwd)
    else:
        # 提示用户输入密码
        try:
            password = getpass.getpass("请输入密码: ")
        except getpass.GetPassWarning:
            print("警告: 在当前环境中无法隐藏密码输入，密码可能会显示在屏幕上")
            password = input("请输入密码: ")
        if len(password) > 0:
            gl_ui.run(file_path, user_input_args.openId, password)


if __name__ == '__main__':
    main()
