#!/usr/bin/env python3
# coding=utf-8
# @Date: 2024-06-30
# @LastEditTime: 2024-07-02
import os
import sys

from PyQt6.QtCore import QCoreApplication

QCoreApplication.setApplicationName("zhmm")
QCoreApplication.setOrganizationName("szgenle")  # 替换为您的组织名称

# 获取当前脚本的绝对路径，并推导出项目根目录（假设项目根目录是包含 `project` 的目录）
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)  # 向上回退两级到项目根目录
sys.path.append(project_root)  # 将项目根目录添加到模块搜索路径
sys.path.append(current_dir)  # 将项目根目录添加到模块搜索路径
utils_dir = os.path.join(current_dir, 'utils')
sys.path.append(utils_dir)

from utils.log import logger
import cmd_main as cmd_main


def main():
    cmd_main.main()
    pass


if __name__ == '__main__':
    logger.debug("调试信息")  # 仅当设置DEBUG级别时可见
    logger.info("常规信息")  # 会写入info.log和控制台
    logger.warning("警告信息")  # 会写入info.log（因为INFO处理器接受WARNING）
    logger.error("错误信息")  # 会写入error.log和控制台
    logger.critical("严重错误")  # 会写入error.log和控制台
    main()
