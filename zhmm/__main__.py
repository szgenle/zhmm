"""统一入口：`python -m zhmm`。

支持的用法：

    python -m zhmm              # 启动 GUI（默认）
    python -m zhmm cli [args]   # 启动 CLI，其余参数原样转发给 cli.commands.main
    python -m zhmm gui          # 显式指定 GUI

也可以通过 pyproject 的 `[project.scripts]` 别名：

    zhmm                        → zhmm.__main__:main   (GUI)
    zhmm-cli                    → zhmm.app.cli_app:main (CLI)
"""

from __future__ import annotations

import sys


def main() -> None:
    """入口函数：根据首参分发 GUI / CLI。"""
    argv = sys.argv[1:]

    # 识别 "cli" / "gui" 子命令，注意首参可能已经是 argparse 参数（如 -i xxx）
    # 规则：只有当首参明确为 "cli" 或 "gui" 时才切模式，其他情况都走 GUI
    if argv and argv[0] == "cli":
        # 把 "cli" 从 argv 里剥掉，剩余原样交给 commands.main 的 argparse
        sys.argv = [sys.argv[0], *argv[1:]]
        from zhmm.cli.commands import main as cli_main

        cli_main()
        return

    if argv and argv[0] == "gui":
        sys.argv = [sys.argv[0], *argv[1:]]

    # 默认：GUI
    from zhmm.app.gui_app import main as gui_main

    # 初始化应用配置与日志（跟老 main.py 行为一致）
    import zhmm
    from zhmm.utils.log import setup_logging

    zhmm.init_app()
    setup_logging()
    gui_main()


if __name__ == "__main__":
    main()
