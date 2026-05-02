"""pytest 全局配置。

- 在无显示器环境（CI、headless）下，强制 Qt 使用 offscreen 平台插件，
  避免因 `zhmm/__init__.py` 间接加载 PyQt6 时找不到显示环境而报错。
- 将 Argon2id KDF 参数压到最低（m=8 KiB, t=1, p=1），避免每个 seal/open
  都耗时 300-500 ms；生产默认参数（见 ``zhmm.core.crypto`` 模块常量）
  对测试结果无影响，只是性能参数，通过头部内嵌机制可被任意覆盖。
"""

import os

# 必须在任何 PyQt6 import 之前设置。
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# ruff: noqa: E402
from zhmm.core import crypto as _crypto

_crypto.ARGON2_M_COST = 8  # type: ignore[misc]
_crypto.ARGON2_T_COST = 1  # type: ignore[misc]
_crypto.ARGON2_P_COST = 1  # type: ignore[misc]
