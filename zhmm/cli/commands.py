#!/usr/bin/env python3
"""命令行子命令解析入口。"""

from __future__ import annotations

import argparse
import getpass
import sys

from zhmm.cli.interactive import CmdUI
from zhmm.utils.log import logger, setup_logging


def main() -> None:
    # 初始化日志系统
    setup_logging()

    parser = argparse.ArgumentParser(description="Process some integers.")
    parser.add_argument("--input", "-i", type=str, help="要加载的加密文件路径")
    parser.add_argument("--out", "-o", type=str, help="输出的文件路径")
    parser.add_argument("--openId", type=str, default="", help="（可选）用户标识，仅作为签名兼容参数")
    parser.add_argument("--pwd", type=str, help="密码，不设置将在随后提醒输入")
    parser.add_argument("--search", "-s", type=str, help="搜索")
    parser.add_argument("--find", "-f", action="store_true", help="查找")
    parser.add_argument("--new", "-n", action="store_true", help="增加")
    parser.add_argument("--modify", "-m", action="store_true", help="修改")
    parser.add_argument("--export", "-e", type=str, help="导出的文件路径")
    parser.add_argument("--delete", "-d", type=str, help="要删除记录的ID")
    parser.add_argument("--simple", action="store_true", help="简单模式（仅允许查询功能）")
    parser.add_argument("--once", action="store_true", help="仅执行一次操作后退出")

    user_input_args = parser.parse_args()
    gl_ui = CmdUI(user_input_args)

    file_path = "zhmm.gl"
    if user_input_args.input:
        file_path = user_input_args.input
    else:
        user_input_args.input = file_path

    try:
        if user_input_args.pwd:
            logger.info("开始执行命令行任务（已提供密码）")
            gl_ui.run(file_path, user_input_args.openId, user_input_args.pwd)
        else:
            # 提示用户输入密码
            try:
                password = getpass.getpass("请输入密码: ")
            except KeyboardInterrupt:
                logger.warning("用户取消输入密码")
                sys.exit(130)  # Ctrl-C
            except Exception:
                logger.warning("当前环境无法隐藏密码输入，将使用明文输入")
                password = input("请输入密码: ")
            if len(password) > 0:
                logger.info("开始执行命令行任务（用户输入密码）")
                gl_ui.run(file_path, user_input_args.openId, password)
            else:
                logger.error("密码不能为空")
                sys.exit(3)
    except Exception:
        logger.exception("命令行任务执行失败: ")
        sys.exit(1)


if __name__ == "__main__":
    main()
