"""剪贴板敏感信息复制工具。

统一处理「复制敏感文本 + 延时自动清空」的模式，相比直接使用
``QTimer.singleShot(10000, clipboard.clear)`` 的简易写法，本模块额外做了
**竞态保护**：

- 记录复制时文本的 SHA-256 截断指纹；
- 10 秒计时器触发时，比对当前剪贴板内容指纹，
  如果用户在此期间已手动复制了别的内容，则放弃清空，
  避免"用户刚复制的东西被我们误清"的体验问题。

使用 SHA-256 而非直接保存明文，避免敏感字符串在闭包里多驻留 10 秒。
"""

from __future__ import annotations

import contextlib
import hashlib

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication

# 默认自动清空延时（毫秒）
DEFAULT_CLEAR_DELAY_MS = 10_000


def _fingerprint(text: str) -> bytes:
    """对敏感文本计算 16B 指纹，用于事后比对而不驻留明文。"""
    return hashlib.sha256(text.encode("utf-8")).digest()[:16]


def copy_sensitive(text: str, delay_ms: int = DEFAULT_CLEAR_DELAY_MS) -> bool:
    """把 ``text`` 复制到剪贴板，并在 ``delay_ms`` 毫秒后尝试清空。

    清空前会比对当前剪贴板内容指纹，若已被用户改写（复制了别的内容），
    则不做任何操作。

    Args:
        text: 敏感明文（密码、动态码、账号等）。空串会被忽略并返回 False。
        delay_ms: 自动清空延时，默认 10 秒。<=0 表示不安排清空。

    Returns:
        True 表示已写入剪贴板并安排了清空（或指定不清空）。
    """
    if not text:
        return False
    clipboard = QApplication.clipboard()
    if clipboard is None:
        return False

    clipboard.setText(text)
    if delay_ms <= 0:
        return True

    expected = _fingerprint(text)

    def _clear_if_unchanged() -> None:
        # 10 秒后的 slot：若 QApplication 已退出，clipboard() 会抛 RuntimeError。
        try:
            cb = QApplication.clipboard()
            if cb is None:
                return
            current = cb.text() or ""
        except RuntimeError:
            return
        if _fingerprint(current) == expected:
            with contextlib.suppress(RuntimeError):
                cb.clear()

    QTimer.singleShot(delay_ms, _clear_if_unchanged)
    return True


__all__ = ["DEFAULT_CLEAR_DELAY_MS", "copy_sensitive"]
