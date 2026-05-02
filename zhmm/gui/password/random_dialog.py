import random
import string

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
)

from zhmm.widgets.strength_bar import PasswordStrengthBar


class RandomPasswordDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("生成随机密码")
        # 原先 setFixedSize(400, 200) 容纳不下自绘的 100x36 按钮行，放宽一点
        self.setFixedSize(420, 240)

        layout = QVBoxLayout()

        # 密码长度设置
        self.length_spin = QSpinBox()
        self.length_spin.setRange(8, 32)
        self.length_spin.setValue(12)

        self.length_slider = QSlider(Qt.Orientation.Horizontal)
        self.length_slider.setRange(8, 32)
        self.length_slider.setValue(12)

        # 联动滑块和微调框
        self.length_spin.valueChanged.connect(self.length_slider.setValue)
        self.length_slider.valueChanged.connect(self.length_spin.setValue)

        length_layout = QHBoxLayout()
        length_layout.addWidget(self.length_spin)
        length_layout.addWidget(self.length_slider)

        # 生成按钮
        generate_btn = QPushButton("立即生成")
        generate_btn.clicked.connect(self.generate_password)

        # 密码显示框
        self.password_edit = QLineEdit()
        self.password_edit.setReadOnly(True)

        # 强度条：setText 也会触发 textChanged，所以直接连即可
        self.password_strength_bar = PasswordStrengthBar()
        self.password_edit.textChanged.connect(self.password_strength_bar.set_password)

        # 底部按钮行：样式与 AddPasswordDialog / AddRoleDialog 对齐
        # （100x36、水平居中、间距 15）。
        # 这里语义上是“采纳该随机密码”，文案用“确认使用”比“确认添加”更贴切。
        button_layout = QHBoxLayout()
        button_layout.setSpacing(15)
        button_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.confirm_button = QPushButton("确认使用")
        self.confirm_button.setObjectName("confirm_button")
        self.confirm_button.setFixedSize(100, 36)
        self.confirm_button.setDefault(True)
        self.confirm_button.setAutoDefault(True)
        self.confirm_button.clicked.connect(self.accept)
        button_layout.addWidget(self.confirm_button)

        cancel_button = QPushButton("取消")
        cancel_button.setObjectName("cancel_button")
        cancel_button.setFixedSize(100, 36)
        cancel_button.setAutoDefault(False)
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        layout.addLayout(length_layout)
        layout.addWidget(generate_btn)
        layout.addWidget(self.password_edit)
        layout.addWidget(self.password_strength_bar)
        layout.addLayout(button_layout)
        self.setLayout(layout)

    def generate_password(self):
        """生成随机密码"""
        length = self.length_spin.value()
        characters = string.ascii_letters + string.digits + "!@#$%^&*"
        password = "".join(random.choice(characters) for _ in range(length))
        self.password_edit.setText(password)

    def get_password(self):
        return self.password_edit.text()
