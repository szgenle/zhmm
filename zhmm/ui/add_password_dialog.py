from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QDialog, QLabel, QFormLayout, QComboBox, QLineEdit, QHBoxLayout, QPushButton, QVBoxLayout

from zhmm.utils import date_util


class AddPasswordDialog(QDialog):
    """添加密码对话框"""

    def __init__(self, parent=None, edit_data=None):
        super().__init__(parent)
        self.setWindowTitle("添加账号密码")
        self.setFixedSize(500, 400)

        # 创建布局
        layout = QVBoxLayout()

        # 标题标签
        title_label = QLabel("请输入账号密码信息")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        layout.addWidget(title_label)

        # 添加一些间距
        layout.addSpacing(20)

        # 创建表单布局
        form_layout = QFormLayout()

        # 类别选择
        self.role_combo = QComboBox()
        self.role_combo.addItems(["个人", "其他"])
        form_layout.addRow("类别:", self.role_combo)

        # 账号输入
        self.userid_input = QLineEdit()
        self.userid_input.setPlaceholderText("请输入账号")
        form_layout.addRow("账号:", self.userid_input)

        # 密码输入
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("请输入密码")
        form_layout.addRow("密码:", self.password_input)

        # 手机输入
        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("请输入手机号码（可选）")
        form_layout.addRow("手机:", self.phone_input)

        # 邮箱输入
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("请输入邮箱（可选）")
        form_layout.addRow("邮箱:", self.email_input)

        # 网站输入
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("请输入网站地址（可选）")
        form_layout.addRow("网站:", self.url_input)

        # 备注输入
        self.desc_input = QLineEdit()
        self.desc_input.setPlaceholderText("请输入备注信息（可选）")
        form_layout.addRow("备注:", self.desc_input)

        layout.addLayout(form_layout)

        # 添加一些间距
        layout.addSpacing(20)

        # 按钮布局
        button_layout = QHBoxLayout()

        # 确认按钮
        self.confirm_button = QPushButton("确认添加")
        button_layout.addWidget(self.confirm_button)

        # 取消按钮
        cancel_button = QPushButton("取消")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        layout.addLayout(button_layout)

        self.setLayout(layout)

        # 如果是编辑模式，填充数据
        if edit_data:
            self._populate_data(edit_data)

    def _populate_data(self, data):
        """填充编辑数据"""
        index = self.role_combo.findText(data['role'])
        if index >= 0:
            self.role_combo.setCurrentIndex(index)
        self.userid_input.setText(data['userID'])
        self.password_input.setText(data['pwd'])
        self.phone_input.setText(data.get('phone', ''))
        self.email_input.setText(data.get('email', ''))
        self.url_input.setText(data.get('url', ''))
        self.desc_input.setText(data.get('desc', ''))

    def get_password_data(self):
        """获取表单数据"""
        return {
            'id': date_util.timestamp_int(),
            'role': self.role_combo.currentText(),
            'userID': self.userid_input.text().strip(),
            'pwd': self.password_input.text().strip(),
            'phone': self.phone_input.text().strip(),
            'email': self.email_input.text().strip(),
            'url': self.url_input.text().strip(),
            'desc': self.desc_input.text().strip(),
            'utime': date_util.timestamp_int()
        }

