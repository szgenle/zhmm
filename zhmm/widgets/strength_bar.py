"""密码强度条 widget。

一条紧凑的水平进度条 + 右侧等级文字。接入方式：

```python
from zhmm.widgets.strength_bar import PasswordStrengthBar

bar = PasswordStrengthBar()
password_input.textChanged.connect(bar.set_password)
```

颜色映射遵循项目主题色板（danger / warning / success 系列），
通过代码动态 setStyleSheet 绘制 chunk 颜色，不依赖全局 QSS。
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QProgressBar, QWidget

from zhmm.core.password_strength import StrengthLevel, assess_strength

# 各等级颜色：红 → 橙 → 黄 → 浅绿 → 深绿，与 theme.py 主题色体系对齐
_LEVEL_COLOR: dict[StrengthLevel, str] = {
    StrengthLevel.VERY_WEAK: "#c62828",
    StrengthLevel.WEAK: "#f57c00",
    StrengthLevel.FAIR: "#fbc02d",
    StrengthLevel.STRONG: "#7cb342",
    StrengthLevel.VERY_STRONG: "#2e7d32",
}


class PasswordStrengthBar(QWidget):
    """密码强度可视化条。

    组成：`QProgressBar`（0-100）+ 右侧 `QLabel`（等级 + 可选改进建议）。
    调用 :meth:`set_password` 传入当前密码原文即可自动评估并更新显示。
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()
        # 初始态：空密码 → 极弱、空建议，不占用视觉焦点
        self.set_password("")

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(8)

        self._bar = QProgressBar(self)
        self._bar.setRange(0, 100)
        self._bar.setTextVisible(False)
        self._bar.setFixedHeight(8)
        layout.addWidget(self._bar, stretch=1)

        self._label = QLabel(self)
        self._label.setMinimumWidth(140)
        self._label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self._label, stretch=0)

    def set_password(self, password: str) -> None:
        """根据新的密码文本刷新强度条与标签。可直接作为 `textChanged` 槽。"""
        result = assess_strength(password)
        color = _LEVEL_COLOR[result.level]

        self._bar.setValue(result.score)
        self._bar.setStyleSheet(
            "QProgressBar {"
            "  background-color: #e0e0e0;"
            "  border: none;"
            "  border-radius: 4px;"
            "}"
            f"QProgressBar::chunk {{"
            f"  background-color: {color};"
            f"  border-radius: 4px;"
            f"}}"
        )

        text = result.label
        # 非空密码 + 有建议时，附上一条最相关的改进提示
        if password and result.hint:
            text = f"{result.label} · {result.hint}"
        self._label.setText(text)
        self._label.setStyleSheet(f"color: {color}; font-size: 12px; background: transparent;")

    def reset(self) -> None:
        """清零，用于对话框重置/重新打开。"""
        self.set_password("")
