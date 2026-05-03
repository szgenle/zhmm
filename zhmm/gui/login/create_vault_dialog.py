#!/usr/bin/env python3
"""新建账号小本本（密码库）向导对话框。

整合原先分散的三步流程（选保存位置 → 是否创建确认 → 登录窗输入账号密码）为
单一向导弹窗，提供：

- 保存位置：可编辑输入框 + ``浏览...`` 按钮（自动补 ``.zmb`` 后缀）
- 账号名：下方一行灰色小字提示"账号与密码共同参与密钥派生，创建后无法修改"
- 主密码 + 确认密码：两个独立输入框，实时校验一致性
- 密码强度条：实时反馈评级与改进建议
- 创建按钮：表单未满足时禁用（灰态），避免无效提交

本对话框只负责采集输入，通过 :attr:`vault_create_requested` 信号把
``(file_path, info_dict)`` 交给上层业务执行真正的加密落盘。
"""

from __future__ import annotations

import os
from pathlib import Path

import bcrypt
from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtGui import QFont, QShowEvent
from PyQt6.QtWidgets import (
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

import zhmm
from zhmm.gui.login.login_window import _to_halfwidth
from zhmm.utils.anti_capture import apply_anti_capture
from zhmm.widgets.dialog import Dialog
from zhmm.widgets.eye_icon import EYE_CLOSED_SVG, EYE_OPEN_SVG, svg_to_icon
from zhmm.widgets.strength_bar import PasswordStrengthBar

_ACCOUNT_HINT = "账号将与密码共同参与密钥派生，创建后无法修改，请慎重填写。"
_VAULT_SUFFIX = ".zmb"


class CreateVaultDialog(Dialog):
    """新建账号小本本向导。

    成功时发出 :attr:`vault_create_requested` 信号，上层负责真正执行创建。
    """

    # (file_path: str, info: dict{account, password, hashpw})
    vault_create_requested = pyqtSignal(str, dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("新建账号小本本")
        self.setMinimumWidth(480)
        self.resize(520, 440)
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint)
        self.setModal(True)

        self._icon_eye_open = svg_to_icon(EYE_OPEN_SVG)
        self._icon_eye_closed = svg_to_icon(EYE_CLOSED_SVG)

        self._build_ui()
        self._wire_signals()
        self._refresh_create_enabled()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        root = QVBoxLayout()

        title = QLabel("新建账号小本本")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        root.addWidget(title)
        root.addSpacing(12)

        input_min_height = 32
        form = QGridLayout()
        form.setHorizontalSpacing(10)
        form.setVerticalSpacing(10)
        row = 0

        # ---------- 保存位置 ----------
        form.addWidget(QLabel("保存位置:"), row, 0)
        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("点击右侧『浏览...』选择保存位置，或直接输入路径")
        self.path_input.setMinimumHeight(input_min_height)

        self.browse_button = QPushButton("浏览...")
        self.browse_button.setMinimumHeight(input_min_height)
        self.browse_button.setFixedWidth(80)

        path_row = QHBoxLayout()
        path_row.setContentsMargins(0, 0, 0, 0)
        path_row.addWidget(self.path_input)
        path_row.addWidget(self.browse_button)
        form.addLayout(path_row, row, 1)
        row += 1

        self.path_hint = QLabel(f"文件将以 {_VAULT_SUFFIX} 格式保存，若路径未带后缀会自动补全。")
        self.path_hint.setStyleSheet("color: #888; font-size: 12px;")
        form.addWidget(self.path_hint, row, 1)
        row += 1

        # ---------- 账号 ----------
        form.addWidget(QLabel("账号名:"), row, 0)
        self.account_input = QLineEdit()
        self.account_input.setPlaceholderText("请输入账号名")
        self.account_input.setMinimumHeight(input_min_height)
        form.addWidget(self.account_input, row, 1)
        row += 1

        self.account_hint = QLabel(_ACCOUNT_HINT)
        self.account_hint.setWordWrap(True)
        self.account_hint.setStyleSheet("color: #888; font-size: 12px;")
        form.addWidget(self.account_hint, row, 1)
        row += 1

        # ---------- 密码 ----------
        form.addWidget(QLabel("主密码:"), row, 0)
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("请输入主密码（半角）")
        self.password_input.setMinimumHeight(input_min_height)

        self.toggle_password_button = QPushButton()
        self.toggle_password_button.setIcon(self._icon_eye_closed)
        self.toggle_password_button.setIconSize(QSize(18, 18))
        self.toggle_password_button.setCheckable(True)
        self.toggle_password_button.setFixedWidth(36)
        self.toggle_password_button.setMinimumHeight(input_min_height)
        self.toggle_password_button.setToolTip("显示/隐藏密码")
        self.toggle_password_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        pwd_row = QHBoxLayout()
        pwd_row.setContentsMargins(0, 0, 0, 0)
        pwd_row.addWidget(self.password_input)
        pwd_row.addWidget(self.toggle_password_button)
        form.addLayout(pwd_row, row, 1)
        row += 1

        # 强度条
        self.password_strength_bar = PasswordStrengthBar()
        form.addWidget(self.password_strength_bar, row, 1)
        row += 1

        # ---------- 确认密码 ----------
        form.addWidget(QLabel("确认密码:"), row, 0)
        self.confirm_input = QLineEdit()
        self.confirm_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_input.setPlaceholderText("请再次输入主密码")
        self.confirm_input.setMinimumHeight(input_min_height)

        self.toggle_confirm_button = QPushButton()
        self.toggle_confirm_button.setIcon(self._icon_eye_closed)
        self.toggle_confirm_button.setIconSize(QSize(18, 18))
        self.toggle_confirm_button.setCheckable(True)
        self.toggle_confirm_button.setFixedWidth(36)
        self.toggle_confirm_button.setMinimumHeight(input_min_height)
        self.toggle_confirm_button.setToolTip("显示/隐藏密码")
        self.toggle_confirm_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        confirm_row = QHBoxLayout()
        confirm_row.setContentsMargins(0, 0, 0, 0)
        confirm_row.addWidget(self.confirm_input)
        confirm_row.addWidget(self.toggle_confirm_button)
        form.addLayout(confirm_row, row, 1)
        row += 1

        self.match_hint = QLabel("")
        self.match_hint.setStyleSheet("font-size: 12px;")
        form.addWidget(self.match_hint, row, 1)
        row += 1

        root.addLayout(form)
        root.addSpacing(16)

        # ---------- 按钮 ----------
        button_row = QHBoxLayout()
        self.create_button = QPushButton("创建")
        self.create_button.setEnabled(False)
        self.create_button.setDefault(True)
        self.cancel_button = QPushButton("取消")
        button_row.addStretch()
        button_row.addWidget(self.create_button)
        button_row.addWidget(self.cancel_button)
        button_row.addStretch()
        root.addLayout(button_row)

        self.setLayout(root)

    def _wire_signals(self) -> None:
        self.browse_button.clicked.connect(self._on_browse)

        self.path_input.textEdited.connect(lambda _t: self._normalize(self.path_input))
        self.path_input.textChanged.connect(self._refresh_create_enabled)

        self.account_input.textEdited.connect(lambda _t: self._normalize(self.account_input))
        self.account_input.textChanged.connect(self._refresh_create_enabled)

        self.password_input.textEdited.connect(lambda _t: self._normalize(self.password_input))
        self.password_input.textChanged.connect(self.password_strength_bar.set_password)
        self.password_input.textChanged.connect(self._refresh_match_hint)
        self.password_input.textChanged.connect(self._refresh_create_enabled)

        self.confirm_input.textEdited.connect(lambda _t: self._normalize(self.confirm_input))
        self.confirm_input.textChanged.connect(self._refresh_match_hint)
        self.confirm_input.textChanged.connect(self._refresh_create_enabled)

        self.toggle_password_button.toggled.connect(
            lambda c: self._toggle_echo(self.password_input, self.toggle_password_button, c)
        )
        self.toggle_confirm_button.toggled.connect(
            lambda c: self._toggle_echo(self.confirm_input, self.toggle_confirm_button, c)
        )

        self.create_button.clicked.connect(self._on_create)
        self.cancel_button.clicked.connect(self.reject)

    # ------------------------------------------------------------------
    # 行为
    # ------------------------------------------------------------------
    def _normalize(self, line_edit: QLineEdit) -> None:
        """实时将输入框中的全角字符纠正为半角。"""
        original = line_edit.text()
        normalized = _to_halfwidth(original)
        if normalized == original:
            return
        cursor = line_edit.cursorPosition()
        line_edit.blockSignals(True)
        try:
            line_edit.setText(normalized)
            line_edit.setCursorPosition(min(cursor, len(normalized)))
        finally:
            line_edit.blockSignals(False)

    def _toggle_echo(self, line_edit: QLineEdit, button: QPushButton, checked: bool) -> None:
        if checked:
            line_edit.setEchoMode(QLineEdit.EchoMode.Normal)
            button.setIcon(self._icon_eye_open)
        else:
            line_edit.setEchoMode(QLineEdit.EchoMode.Password)
            button.setIcon(self._icon_eye_closed)

    def _on_browse(self) -> None:
        current = self.path_input.text().strip() or str(Path.home())
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "选择新建账号小本本的保存位置",
            current,
            f"账号小本本 (*{_VAULT_SUFFIX})",
        )
        if file_path:
            self.path_input.setText(file_path)

    def _refresh_match_hint(self) -> None:
        pwd = self.password_input.text()
        confirm = self.confirm_input.text()
        if not confirm:
            self.match_hint.setText("")
            return
        if pwd == confirm:
            self.match_hint.setText("✓ 两次输入一致")
            self.match_hint.setStyleSheet("color: #2e7d32; font-size: 12px;")
        else:
            self.match_hint.setText("✗ 两次输入不一致")
            self.match_hint.setStyleSheet("color: #c62828; font-size: 12px;")

    def _refresh_create_enabled(self) -> None:
        ok = (
            bool(self.path_input.text().strip())
            and bool(self.account_input.text().strip())
            and bool(self.password_input.text())
            and self.password_input.text() == self.confirm_input.text()
        )
        self.create_button.setEnabled(ok)

    def _on_create(self) -> None:
        raw_path = _to_halfwidth(self.path_input.text()).strip()
        account = _to_halfwidth(self.account_input.text()).strip()
        password = _to_halfwidth(self.password_input.text()).strip()
        confirm = _to_halfwidth(self.confirm_input.text()).strip()

        if not raw_path:
            self._warn("请指定保存位置")
            return
        if not account:
            self._warn("账号名不能为空")
            return
        if not password:
            self._warn("主密码不能为空")
            return
        if password != confirm:
            self._warn("两次输入的密码不一致")
            return

        # 规范化路径：确保 .zmb 后缀 + 父目录存在
        file_path = raw_path
        if not file_path.lower().endswith(_VAULT_SUFFIX):
            file_path += _VAULT_SUFFIX

        parent_dir = os.path.dirname(file_path) or "."
        if not os.path.isdir(parent_dir):
            self._warn(f"保存目录不存在：\n{parent_dir}")
            return

        if os.path.exists(file_path):
            confirm_box = QMessageBox(self)
            confirm_box.setIcon(QMessageBox.Icon.Warning)
            confirm_box.setWindowTitle("文件已存在")
            confirm_box.setText(f"文件已存在：\n{file_path}\n\n继续将覆盖原文件，原有数据将无法恢复。是否继续？")
            confirm_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            confirm_box.setDefaultButton(QMessageBox.StandardButton.No)
            if confirm_box.exec() != QMessageBox.StandardButton.Yes:
                return

        hashpw = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode("utf-8")
        info = {
            "account": account,
            "password": password,
            "hashpw": hashpw,
        }
        self.vault_create_requested.emit(file_path, info)
        self.accept()

    def _warn(self, msg: str) -> None:
        QMessageBox.warning(self, "提示", msg)

    # ------------------------------------------------------------------
    # 生命周期
    # ------------------------------------------------------------------
    def showEvent(self, event: QShowEvent):  # type: ignore[override]
        super().showEvent(event)
        enabled = True
        if zhmm.setting is not None:
            enabled = zhmm.setting.get_anti_screenshot()
        apply_anti_capture(self, enabled=enabled)
