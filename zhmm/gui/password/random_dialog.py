import random
import string

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
)


class RandomPasswordDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("生成随机密码")
        self.setFixedSize(400, 200)

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

        # 按钮框
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        layout.addLayout(length_layout)
        layout.addWidget(generate_btn)
        layout.addWidget(self.password_edit)
        layout.addWidget(button_box)
        self.setLayout(layout)

    def generate_password(self):
        """生成随机密码"""
        length = self.length_spin.value()
        characters = string.ascii_letters + string.digits + "!@#$%^&*"
        password = "".join(random.choice(characters) for _ in range(length))
        self.password_edit.setText(password)

    def get_password(self):
        return self.password_edit.text()
