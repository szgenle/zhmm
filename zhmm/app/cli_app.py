"""CLI 入口（给 `poetry run zhmm-cli` 使用）。

薄包装，转发到 [zhmm.cli.commands][]。真正的 argparse / 交互在那边实现。
"""

from __future__ import annotations

from zhmm.cli.commands import main as _cli_main


def main() -> None:
    """CLI 启动入口。"""
    _cli_main()


if __name__ == "__main__":
    main()
