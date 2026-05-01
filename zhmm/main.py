#!/usr/bin/env python3
# coding=utf-8
# @Date: 2024-06-30
# @LastEditTime: 2024-07-02

import zhmm
from zhmm import ui_app
from zhmm.utils.log import setup_logging


def main():
    # 初始化应用配置
    zhmm.init_app()

    # 初始化日志系统
    setup_logging()

    # 启动 UI 应用
    ui_app.main()


if __name__ == "__main__":
    # logger.debug("调试信息")  # 仅当设置DEBUG级别时可见
    # logger.info("常规信息")  # 会写入info.log和控制台
    # logger.warning("警告信息")  # 会写入info.log（因为INFO处理器接受WARNING）
    # logger.error("错误信息")  # 会写入error.log和控制台
    # logger.critical("严重错误")  # 会写入error.log和控制台
    main()
