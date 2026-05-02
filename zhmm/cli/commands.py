#!/usr/bin/env python3
"""命令行子命令解析入口。"""

from __future__ import annotations

import argparse
import getpass
import sys


def _build_parser(include_data_dir: bool = False) -> argparse.ArgumentParser:
    epilog: str | None = None
    if include_data_dir:
        # 仅在 --help 场景展示数据目录，避免走到业务流程时刷屏
        from zhmm.utils.file_util import get_writable_dir

        epilog = f"数据目录: {get_writable_dir()}"
    parser = argparse.ArgumentParser(
        description="Process some integers.",
        epilog=epilog,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--input", "-i", type=str, help="要加载的加密文件路径")
    parser.add_argument("--out", "-o", type=str, help="输出的文件路径")
    parser.add_argument("--account", type=str, default=None, help="账号名（与密码共同生成密钥，必填）")
    parser.add_argument("--pwd", type=str, help="密码，不设置将在随后提醒输入")
    parser.add_argument("--search", "-s", type=str, help="搜索")
    parser.add_argument("--find", "-f", action="store_true", help="查找")
    parser.add_argument("--new", "-n", action="store_true", help="增加")
    parser.add_argument("--modify", "-m", action="store_true", help="修改")
    parser.add_argument("--export", "-e", type=str, help="导出的文件路径")
    parser.add_argument("--delete", "-d", type=str, help="要删除记录的ID")
    parser.add_argument(
        "--totp",
        type=int,
        metavar="ID",
        help="打印指定条目的当前 TOTP 验证码与剩余秒数后退出",
    )
    parser.add_argument("--simple", action="store_true", help="简单模式（仅允许查询功能）")
    parser.add_argument("--once", action="store_true", help="仅执行一次操作后退出")
    return parser


def main() -> None:
    # --help 快通道：避免做 setup_logging / 入业务的重操作，仅此时展示数据目录
    # argparse 在遇到 -h/--help 时会自行 sys.exit(0)
    if any(arg in ("-h", "--help") for arg in sys.argv[1:]):
        _build_parser(include_data_dir=True).parse_args()
        return

    # 真正进入业务流程时再初始化日志 & 懒加载 CmdUI
    from zhmm.cli.interactive import CmdUI
    from zhmm.utils.log import logger, setup_logging

    setup_logging()

    user_input_args = _build_parser().parse_args()
    gl_ui = CmdUI(user_input_args)

    file_path = "zhmm.zmb"
    if user_input_args.input:
        file_path = user_input_args.input
    else:
        user_input_args.input = file_path

    # 账号：未提供时交互式读取，空值直接退出
    account = user_input_args.account
    if account is None:
        try:
            account = input("请输入账号名: ").strip()
        except KeyboardInterrupt:
            logger.warning("用户取消输入账号名")
            sys.exit(130)
    if not account:
        logger.error("账号名不能为空")
        sys.exit(3)
    user_input_args.account = account

    try:
        if user_input_args.pwd:
            logger.info("开始执行命令行任务（已提供密码）")
            gl_ui.run(file_path, account, user_input_args.pwd)
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
                gl_ui.run(file_path, account, password)
            else:
                logger.error("密码不能为空")
                sys.exit(3)
    except Exception:
        logger.exception("命令行任务执行失败: ")
        sys.exit(1)


if __name__ == "__main__":
    main()
