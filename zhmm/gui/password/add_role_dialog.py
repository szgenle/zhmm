"""新建类别对话框。

替代原来由 `AddPasswordDialog._add_custom_role` 使用的 `QInputDialog.getText`，
目的：
1. 按钮文字 / 尺寸 / 居中排列与父对话框 `AddPasswordDialog` 完全一致
   （「确认添加」「取消」均为 100x36，水平居中，间距 15）。
2. 输入框回车 = 确认，Esc = 取消。
3. 类别名重复 / 为空时，在对话框内红字提示，不再弹新对话框。
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)


class AddRoleDialog(QDialog):
    """新建类别对话框：输入一个字符串、内联校验、回车确认、Esc 取消。"""

    def __init__(self, parent, existing_roles: list[str]):
        super().__init__(parent)
        self.setWindowTitle("新建类别")
        self.setFixedWidth(420)

        # 大小写不敏感去重（与 role_combo 的 findText 默认一致，避免「个人」「ge人」这种
        # 微差被当成不同类别）。原值留一份用于 emit。
        self._existing_lower = {r.strip().lower() for r in (existing_roles or []) if r}

        self._result_role: str = ""  # accept 时外层读取

        layout = QVBoxLayout()
        layout.setContentsMargins(30, 20, 30, 20)
        layout.setSpacing(15)

        # 标题
        title = QLabel("请输入新类别名称")
        title.setObjectName("title_label")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFixedHeight(36)
        layout.addWidget(title)

        # 输入框
        self.input = QLineEdit()
        self.input.setFixedHeight(30)
        self.input.setPlaceholderText("如：工作、生活、开发……")
        self.input.textChanged.connect(self._on_text_changed)
        layout.addWidget(self.input)

        # 页内错误/提示条：始终占一行高度避免重新布局抖动
        self.hint_label = QLabel("")
        self.hint_label.setFixedHeight(20)
        self.hint_label.setStyleSheet("color: #c62828; font-size: 12px;")
        layout.addWidget(self.hint_label)

        # 按钮行
        button_layout = QHBoxLayout()
        button_layout.setSpacing(15)
        button_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.confirm_button = QPushButton("确认添加")
        self.confirm_button.setObjectName("confirm_button")
        self.confirm_button.setFixedSize(100, 36)
        self.confirm_button.setEnabled(False)  # 空输入下禁用
        # setDefault(True) → 输入框按回车会触发它
        self.confirm_button.setDefault(True)
        self.confirm_button.setAutoDefault(True)
        self.confirm_button.clicked.connect(self._on_confirm)
        button_layout.addWidget(self.confirm_button)

        cancel_button = QPushButton("取消")
        cancel_button.setObjectName("cancel_button")
        cancel_button.setFixedSize(100, 36)
        # autoDefault=False 避免它也在回车时被触发
        cancel_button.setAutoDefault(False)
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        layout.addLayout(button_layout)
        self.setLayout(layout)

        # 初始聚焦到输入框
        self.input.setFocus()

    # ------------------------------------------------------------------
    # 事件 / 校验
    # ------------------------------------------------------------------
    def _on_text_changed(self, text: str) -> None:
        """输入变化时做内联校验：空 / 重复。"""
        value = text.strip()
        if not value:
            # 空：禁用确认，清除错误（不显示「不能为空」避免唠叨，交互更柔和）
            self.confirm_button.setEnabled(False)
            self.hint_label.setText("")
            return
        if value.lower() in self._existing_lower:
            self.confirm_button.setEnabled(False)
            self.hint_label.setText("⚠ 该类别已存在")
            return
        # 合法
        self.confirm_button.setEnabled(True)
        self.hint_label.setText("")

    def _on_confirm(self) -> None:
        """点确认或回车：再兜一次校验后 accept。"""
        value = self.input.text().strip()
        if not value:
            return
        if value.lower() in self._existing_lower:
            self.hint_label.setText("⚠ 该类别已存在")
            return
        self._result_role = value
        self.accept()

    def keyPressEvent(self, event: QKeyEvent) -> None:  # type: ignore[override]
        """Esc → 取消。

        QDialog 默认 Esc = reject，这里显式写出来一方面语义更清晰，另一方面避免
        未来某个 parent 覆盖时丢行为。回车不在此处理 —— 交给 confirm_button.setDefault(True)。
        """
        if event.key() == Qt.Key.Key_Escape:
            self.reject()
            return
        super().keyPressEvent(event)

    # ------------------------------------------------------------------
    # 对外接口
    # ------------------------------------------------------------------
    def role_value(self) -> str:
        """accept 后读取用户输入的类别名；reject 时返回空串。"""
        return self._result_role
