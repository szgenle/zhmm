#!/usr/bin/env python3
# @Date: 2024-07-03
# @LastEditTime: 2024-07-03
import bcrypt
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton, QVBoxLayout

from zhmm.utils.log import logger
from zhmm.widgets.dialog import Dialog


def _to_halfwidth(text: str) -> str:
    """将常见全角字符转换为半角。

    覆盖范围：
    - 全角空格(U+3000) -> 普通空格
    - 全角 ASCII 可见字符(U+FF01 ~ U+FF5E) -> 对应的半角字符
    其他字符保持不变。
    """
    result: list[str] = []
    for ch in text:
        code = ord(ch)
        if code == 0x3000:
            result.append(" ")
        elif 0xFF01 <= code <= 0xFF5E:
            result.append(chr(code - 0xFEE0))
        else:
            result.append(ch)
    return "".join(result)


class LoginWindow(Dialog):
    """登录对话框"""

    login_success = pyqtSignal(dict)  # 保持信号声明不变
    hashpw: str | None = None

    def __init__(self, openid: str | None = None, hashpw: str | None = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("登录验证")
        self.setFixedSize(400, 250)
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint)
        self.setModal(True)
        self.hashpw = hashpw

        # 创建布局
        layout = QVBoxLayout()

        # 标题标签
        title_label = QLabel("请输入登录信息")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        layout.addWidget(title_label)

        # 添加一些间距
        layout.addSpacing(20)

        # 创建表单布局
        form_layout = QGridLayout()

        row = 0
        # OpenID输入
        openid_label = QLabel("OpenID:")
        self.openid_input = QLineEdit()
        self.openid_input.setPlaceholderText("请输入微信小程序中显示的OpenId")
        self.openid_input.textEdited.connect(lambda _text: self._normalize_line_edit(self.openid_input))
        if openid:
            self.openid_input.setText(openid)
            self.openid_input.hide()
        else:
            form_layout.addWidget(openid_label, row, 0)
            form_layout.addWidget(self.openid_input, row, 1)
            row += 1

        # 密码输入
        password_label = QLabel("密码:")
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("请输入密码（半角）")
        self.password_input.textEdited.connect(lambda _text: self._normalize_line_edit(self.password_input))

        # 显示/隐藏密码切换按钮
        self.toggle_password_button = QPushButton("显示")
        self.toggle_password_button.setCheckable(True)
        self.toggle_password_button.setFixedWidth(48)
        self.toggle_password_button.setToolTip("显示/隐藏密码")
        self.toggle_password_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.toggle_password_button.toggled.connect(self._toggle_password_visibility)

        password_row_layout = QHBoxLayout()
        password_row_layout.setContentsMargins(0, 0, 0, 0)
        password_row_layout.addWidget(self.password_input)
        password_row_layout.addWidget(self.toggle_password_button)

        form_layout.addWidget(password_label, row, 0)
        form_layout.addLayout(password_row_layout, row, 1)

        layout.addLayout(form_layout)

        # 添加一些间距
        layout.addSpacing(20)

        # 按钮布局
        button_layout = QHBoxLayout()

        # 登录按钮
        self.login_button = QPushButton("登录")
        self.login_button.clicked.connect(lambda: self.verify_login())
        button_layout.addWidget(self.login_button)

        # 取消按钮
        cancel_button = QPushButton("取消")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        layout.addLayout(button_layout)

        self.setLayout(layout)

    def _normalize_line_edit(self, line_edit: QLineEdit) -> None:
        """实时将输入框中的全角字符纠正为半角，避免用户因输入法差异出错。"""
        original = line_edit.text()
        normalized = _to_halfwidth(original)
        if normalized == original:
            return
        cursor_pos = line_edit.cursorPosition()
        line_edit.blockSignals(True)
        try:
            line_edit.setText(normalized)
            line_edit.setCursorPosition(min(cursor_pos, len(normalized)))
        finally:
            line_edit.blockSignals(False)

    def _toggle_password_visibility(self, checked: bool) -> None:
        """切换密码明文/密文显示"""
        if checked:
            self.password_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.toggle_password_button.setText("隐藏")
        else:
            self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.toggle_password_button.setText("显示")

    def verify_login(self):
        """验证登录信息"""
        openid = _to_halfwidth(self.openid_input.text()).strip()
        password = _to_halfwidth(self.password_input.text()).strip()

        if not openid:
            QMessageBox.warning(self, "警告", "OpenID不能为空")
            return

        if not password:
            QMessageBox.warning(self, "警告", "密码不能为空")
            return

        try:
            if self.hashpw and not bcrypt.checkpw(password.encode(), self.hashpw.encode()):
                self.show_error("密码错误")
                return
        except ValueError as e:
            self.show_error(f"认证失败: {str(e)}")
            return

        # 登录成功
        logger.info(f"用户 {openid} 登录成功")
        # 登录成功时需要显式指定字典类型
        hashpw = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode("utf-8")
        info = {
            "openid": openid,
            "password": password,
            "hashpw": hashpw,
        }

        self.login_success.emit(info)  # 直接传递强类型对象
        self.accept()

    def show_error(self, msg):
        QMessageBox.critical(self, "错误", msg)
