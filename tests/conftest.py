"""pytest 全局配置。

- 在无显示器环境（CI、headless）下，强制 Qt 使用 offscreen 平台插件，
  避免因 `zhmm/__init__.py` 间接加载 PyQt6 时找不到显示环境而报错。
"""

import os

# 必须在任何 PyQt6 import 之前设置。
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
