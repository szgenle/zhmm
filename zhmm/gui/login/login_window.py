#!/usr/bin/env python3
# @Date: 2024-07-03
# @LastEditTime: 2024-07-03
import bcrypt
from PyQt6.QtCore import QByteArray, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QFont, QIcon, QPainter, QPixmap, QShowEvent
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton, QVBoxLayout

import zhmm
from zhmm.utils.anti_capture import apply_anti_capture
from zhmm.utils.log import logger
from zhmm.widgets.dialog import Dialog

# 睁眼图标（Feather Icons 风格，适用于“当前显示密码，点击可隐藏”）
_EYE_OPEN_SVG = (
    b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
    b'stroke="#333333" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
    b'<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8S1 12 1 12z"/>'
    b'<circle cx="12" cy="12" r="3"/>'
    b"</svg>"
)

# 闭眼图标（带斜线，适用于“当前隐藏密码，点击可显示”）
_EYE_CLOSED_SVG = (
    b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
    b'stroke="#333333" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
    b'<path d="M17.94 17.94A10.94 10.94 0 0 1 12 20c-7 0-11-8-11-8a19.62 19.62 0 0 1 5.06-5.94"/>'
    b'<path d="M9.9 4.24A10.94 10.94 0 0 1 12 4c7 0 11 8 11 8a19.4 19.4 0 0 1-2.17 3.19"/>'
    b'<path d="M9.88 9.88a3 3 0 0 0 4.24 4.24"/>'
    b'<line x1="1" y1="1" x2="23" y2="23"/>'
    b"</svg>"
)


def _svg_to_icon(svg_data: bytes, size: int = 20) -> QIcon:
    """将内联 SVG 字节串渲染为 QIcon，避免依赖外部资源文件。"""
    renderer = QSvgRenderer(QByteArray(svg_data))
    pixmap = QPixmap(QSize(size, size))
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    try:
        renderer.render(painter)
    finally:
        painter.end()
    return QIcon(pixmap)


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

    def __init__(self, account: str | None = None, hashpw: str | None = None, parent=None):
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
        # 账号输入
        account_label = QLabel("账号名:")
        self.account_input = QLineEdit()
        self.account_input.setPlaceholderText("请输入账号名（与密码共同生成密钥）")
        self.account_input.textEdited.connect(lambda _text: self._normalize_line_edit(self.account_input))
        if account:
            self.account_input.setText(account)
            self.account_input.hide()
        else:
            form_layout.addWidget(account_label, row, 0)
            form_layout.addWidget(self.account_input, row, 1)
            row += 1

        # 密码输入
        password_label = QLabel("密码:")
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("请输入密码（半角）")
        self.password_input.textEdited.connect(lambda _text: self._normalize_line_edit(self.password_input))

        # 显示/隐藏密码切换按钮（使用内联 SVG 图标）
        self._icon_eye_open = _svg_to_icon(_EYE_OPEN_SVG)
        self._icon_eye_closed = _svg_to_icon(_EYE_CLOSED_SVG)
        self.toggle_password_button = QPushButton()
        self.toggle_password_button.setIcon(self._icon_eye_closed)
        self.toggle_password_button.setIconSize(QSize(18, 18))
        self.toggle_password_button.setCheckable(True)
        self.toggle_password_button.setFixedWidth(36)
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
            self.toggle_password_button.setIcon(self._icon_eye_open)
        else:
            self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.toggle_password_button.setIcon(self._icon_eye_closed)

    def showEvent(self, event: QShowEvent):  # type: ignore[override]
        super().showEvent(event)
        # 登录框属于敏感入口，依照全局开关应用防截屏
        enabled = True
        if zhmm.setting is not None:
            enabled = zhmm.setting.get_anti_screenshot()
        apply_anti_capture(self, enabled=enabled)

    def verify_login(self):
        """验证登录信息"""
        account = _to_halfwidth(self.account_input.text()).strip()
        password = _to_halfwidth(self.password_input.text()).strip()

        if not account:
            QMessageBox.warning(self, "警告", "账号名不能为空")
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
        logger.info(f"用户 {account} 登录成功")
        # 登录成功时需要显式指定字典类型
        hashpw = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode("utf-8")
        info = {
            "account": account,
            "password": password,
            "hashpw": hashpw,
        }

        self.login_success.emit(info)  # 直接传递强类型对象
        self.accept()

    def show_error(self, msg):
        QMessageBox.critical(self, "错误", msg)
