"""浏览器填充桥授权对话框。"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QVBoxLayout,
    QWidget,
)


class ApprovalDialog(QDialog):
    """单次填充授权框。

    展示请求方 origin 与目标条目，用户点击「允许」后方会把明文下发。
    勾选「5 分钟内不再问」后，controller 会把 origin 加入临时白名单。
    """

    TRUST_TTL_SECONDS = 300

    def __init__(
        self,
        origin: str,
        entry_user_id: str,
        entry_url: str,
        has_totp: bool,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("浏览器填充请求")
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self.setModal(True)
        self._trust_ttl = 0

        layout = QVBoxLayout(self)
        title = QLabel("<b>浏览器正在请求填充密码</b>")
        layout.addWidget(title)

        # origin 独占一行并用大字，和条目 URL 对照显示，提示用户自查钓鱼
        origin_label = QLabel(f"<div style='font-size:15px;'>请求来源：<code>{origin}</code></div>")
        origin_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(origin_label)

        entry_label = QLabel(
            f"拟填充条目：<b>{entry_user_id or '(未填用户名)'}</b><br>"
            f"条目 URL：<code>{entry_url or '(空)'}</code>" + ("<br>附带 TOTP 动态码" if has_totp else "")
        )
        entry_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(entry_label)

        tip = QLabel(
            "<span style='color:#a33;'>请确认「请求来源」与「条目 URL」主机一致，" "不一致可能是钓鱼页面。</span>"
        )
        tip.setWordWrap(True)
        layout.addWidget(tip)

        self._trust_box = QCheckBox(f"该域名 {self.TRUST_TTL_SECONDS // 60} 分钟内不再询问")
        layout.addWidget(self._trust_box)

        btns = QDialogButtonBox(self)
        allow_btn = btns.addButton("允许", QDialogButtonBox.ButtonRole.AcceptRole)
        deny_btn = btns.addButton("拒绝", QDialogButtonBox.ButtonRole.RejectRole)
        assert allow_btn is not None and deny_btn is not None  # addButton 按类型签名返回 Optional
        allow_btn.clicked.connect(self._on_allow)
        deny_btn.clicked.connect(self.reject)
        # 默认聚焦到「拒绝」，避免回车误操作
        deny_btn.setDefault(True)
        deny_btn.setFocus()
        layout.addWidget(btns)

    def _on_allow(self) -> None:
        if self._trust_box.isChecked():
            self._trust_ttl = self.TRUST_TTL_SECONDS
        self.accept()

    def trust_ttl(self) -> int:
        return self._trust_ttl
