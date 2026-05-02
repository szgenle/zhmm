"""GUI 文案常量骨架。

集中收敛散落在各窗口里的面向用户的短文案（状态栏、气泡、提示等），
便于日后维护、i18n（国际化）预留接口，以及避免同一文案多处硬编码
改漏（典型：复制成功提示在 emit 和 schedule_reset 两处出现）。

## 分组约定

- `Status`：底部状态栏（MainWindow.status_label）文案
- `Tooltip`：鼠标气泡（QToolTip.showText）文案
- `Filter`：搜索/筛选区相关文案

## 使用方式

```python
from zhmm.gui.texts import Status, Tooltip

# 静态文案
self.status_changed.emit(Status.PWD_REVEAL_HIDDEN, "normal")

# 需要动态参数的：走 @staticmethod 工厂
self._show_status(Status.pwd_reveal_visible(duration), highlight=True)
```

## 扩充原则

- 只收敛**面向最终用户**的文案；程序日志 / 异常 message 不纳入
- 带参数的文案用 `@staticmethod` 而非 f-string 模板，防止调用方忘传参
- 文案本身仍用中文硬编码，i18n 真正要做时再切 gettext / Qt tr()
"""

from __future__ import annotations


class Status:
    """底部状态栏文案。"""

    # ---- 筛选状态 ----
    FILTER_EMPTY = "请输入关键字以显示结果"
    FILTER_ALL = "显示全部数据"

    # ---- 密码复制 ----
    PWD_COPIED_WITH_HINT = "✅ 已复制密码到剪贴板（10 秒后自动清空）"

    # ---- 密码明文切换 ----
    PWD_REVEAL_HIDDEN = "🔒 密码已隐藏"
    PWD_REVEAL_AUTO_HIDDEN = "🔒 密码已自动隐藏"

    # ---- TOTP ----
    TOTP_INVALID = "⚠ TOTP 配置无效"

    @staticmethod
    def filter_by(keyword: str) -> str:
        """搜索命中时的状态文案。"""
        return f"已按“{keyword}”筛选"

    @staticmethod
    def pwd_reveal_visible(seconds: int) -> str:
        """密码被显示时带自动隐藏倒计时的文案。"""
        return f"👁 密码已显示，{seconds} 秒后自动隐藏"

    @staticmethod
    def totp_copied_with_hint(code: str) -> str:
        """复制动态码成功（带剪贴板自动清空提示）。"""
        return f"✅ 已复制动态码 {code}（10 秒后自动清空剪贴板）"

    @staticmethod
    def copied_plain(label: str) -> str:
        """复制非敏感字段（账号/网址等）。"""
        return f"✅ 已复制{label}"


class Tooltip:
    """鼠标位置气泡文案。"""

    PWD_COPIED = "✅ 已复制密码到剪贴板"
    TOTP_NOT_ENABLED = "该条目未启用 TOTP"

    @staticmethod
    def copied_plain(label: str) -> str:
        return f"✅ 已复制{label}"

    @staticmethod
    def totp_copied(code: str) -> str:
        return f"✅ 已复制动态码 {code}"

    @staticmethod
    def totp_invalid(detail: str) -> str:
        return f"⚠ TOTP 配置无效: {detail}"
