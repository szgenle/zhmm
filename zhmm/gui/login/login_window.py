#!/usr/bin/env python3
# @Date: 2024-07-03
# @LastEditTime: 2024-07-03
import bcrypt
from PyQt6.QtCore import QSize, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QShowEvent
from PyQt6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton, QVBoxLayout

import zhmm
from zhmm.utils.anti_capture import apply_anti_capture
from zhmm.utils.log import logger
from zhmm.widgets.dialog import Dialog
from zhmm.widgets.eye_icon import EYE_CLOSED_SVG, EYE_OPEN_SVG, svg_to_icon
from zhmm.widgets.strength_bar import PasswordStrengthBar


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

    # 失败次数限速（UI 层退避）：
    # - 仅用于本对话框会话内连续失败的手动重试限速；
    # - 不防离线暴力（攻击者可直接调用 core.vault 绕过 GUI），离线暴力由 Argon2id 承担。
    _FAIL_THRESHOLD = 3  # 达到此次失败后开始退避
    _BASE_LOCK_SECONDS = 2  # 首次锁定秒数
    _MAX_LOCK_SECONDS = 60  # 单次锁定上限

    def __init__(self, account: str | None = None, hashpw: str | None = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("登录验证")
        self.setFixedSize(400, 250)
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint)
        self.setModal(True)
        self.hashpw = hashpw

        # 失败计数与锁定状态（进程内，重启清零）
        self._fail_count = 0
        self._lock_remaining = 0
        self._lock_timer = QTimer(self)
        self._lock_timer.setInterval(1000)
        self._lock_timer.timeout.connect(self._on_lock_tick)

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

        # 显示/隐藏密码切换按钮（使用共享的内联 SVG 图标）
        self._icon_eye_open = svg_to_icon(EYE_OPEN_SVG)
        self._icon_eye_closed = svg_to_icon(EYE_CLOSED_SVG)
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
        row += 1

        # 密码强度条：仅在「首次设置主密码」与「登录核对」时都能给到参考
        self.password_strength_bar = PasswordStrengthBar()
        self.password_input.textChanged.connect(self.password_strength_bar.set_password)
        form_layout.addWidget(self.password_strength_bar, row, 1)

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
        # 处于锁定期时按钮本应已禁用，此处做二次保护
        if self._lock_remaining > 0:
            return

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
                self._fail_count += 1
                self._handle_failed_attempt()
                return
        except ValueError as e:
            self.show_error(f"认证失败: {str(e)}")
            return

        # 登录成功，重置失败计数
        self._fail_count = 0
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

    def _handle_failed_attempt(self) -> None:
        """处理一次密码错误：未达阈值则提示，达到阈值后进入指数退避锁定。"""
        if self._fail_count < self._FAIL_THRESHOLD:
            self.show_error("密码错误")
            return
        exponent = self._fail_count - self._FAIL_THRESHOLD
        lock_seconds = min(self._BASE_LOCK_SECONDS * (2**exponent), self._MAX_LOCK_SECONDS)
        logger.warning(f"连续登录失败 {self._fail_count} 次，锁定 {lock_seconds}s")
        QMessageBox.critical(
            self,
            "错误",
            f"密码错误\n\n连续失败 {self._fail_count} 次，请等待 {lock_seconds} 秒后重试",
        )
        self._start_lockout(lock_seconds)

    def _start_lockout(self, seconds: int) -> None:
        """开始锁定：禁用登录按钮与密码输入框，启动秒级倒计时。"""
        self._lock_remaining = seconds
        self.login_button.setEnabled(False)
        self.password_input.setEnabled(False)
        self._update_lock_button_text()
        self._lock_timer.start()

    def _on_lock_tick(self) -> None:
        self._lock_remaining -= 1
        if self._lock_remaining <= 0:
            self._end_lockout()
        else:
            self._update_lock_button_text()

    def _end_lockout(self) -> None:
        self._lock_timer.stop()
        self._lock_remaining = 0
        self.login_button.setEnabled(True)
        self.password_input.setEnabled(True)
        self.login_button.setText("登录")
        # 聚焦到密码框，便于继续尝试
        self.password_input.setFocus()

    def _update_lock_button_text(self) -> None:
        self.login_button.setText(f"登录（{self._lock_remaining}s）")

    def show_error(self, msg):
        QMessageBox.critical(self, "错误", msg)
