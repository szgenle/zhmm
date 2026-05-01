"""Legacy 入口薄包装：转发到 [zhmm.__main__.main][]。

保留此文件是为了兼容既有的 `python -m zhmm.main` 调用方式（如 Makefile）。
新代码请使用 `python -m zhmm` 或 `zhmm` / `zhmm-cli` 命令。
"""

from __future__ import annotations

from zhmm.__main__ import main


if __name__ == "__main__":
    main()
