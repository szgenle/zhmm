from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (QComboBox, QDialog, QFormLayout, QHBoxLayout,
                             QInputDialog, QLabel, QLineEdit, QPushButton,
                             QTextEdit, QVBoxLayout)

from zhmm.utils import date_util
from zhmm.window_password.random_password_dialog import RandomPasswordDialog

class AddPasswordDialog(QDialog):
    """添加密码对话框"""

    added_role = pyqtSignal(str)  # 增加角色信息

    def __init__(self, parent, roles: list[str], edit_data=None):
        super().__init__(parent)
        self.setWindowTitle("添加账号密码")
        self.setFixedSize(600, 650)  # 增加高度容纳优化后的布局

        self.roles = roles

        # 创建布局
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 20, 30, 20)  # 增加外间距
        layout.setSpacing(15)  # 统一控件间距

        # 标题标签
        title_label = QLabel("请输入账号密码信息")
        title_label.setObjectName("title_label")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setFixedHeight(40)
        layout.addWidget(title_label)

        # 创建表单布局
        form_layout = QFormLayout()
        form_layout.setSpacing(12)  # 表单控件间距
        form_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        # 类别选择
        self.role_combo = QComboBox()
        self.role_combo.setFixedHeight(36)  # 增加控件高度
        self.role_combo.setEditable(True)
        self.role_combo.addItems(self.roles)

        # 添加新建类别按钮
        add_role_btn = QPushButton("+")
        add_role_btn.setObjectName("add_role_btn")
        add_role_btn.setFixedSize(36, 36)
        add_role_btn.clicked.connect(self._add_custom_role)

        role_layout = QHBoxLayout()
        role_layout.setSpacing(8)
        role_layout.addWidget(self.role_combo)
        role_layout.addWidget(add_role_btn)
        form_layout.addRow("类别:", role_layout)

        # 账号输入
        self.userid_input = QLineEdit()
        self.userid_input.setMinimumWidth(300)
        self.userid_input.setFixedHeight(30)
        self.userid_input.setPlaceholderText("请输入账号")
        form_layout.addRow("账号:", self.userid_input)

        # 密码输入
        self.password_input = QLineEdit()
        self.password_input.setMinimumWidth(300)
        self.password_input.setFixedHeight(30)
        self.password_input.setPlaceholderText("请输入密码")

        # 添加随机密码按钮
        self.random_pwd_btn = QPushButton("随机密码")
        self.random_pwd_btn.setFixedHeight(30)
        self.random_pwd_btn.clicked.connect(self.show_random_pwd_dialog)

        # 将输入框和按钮放入水平布局
        pwd_layout = QHBoxLayout()
        pwd_layout.addWidget(self.password_input, stretch=4)
        pwd_layout.addWidget(self.random_pwd_btn, stretch=1)

        form_layout.addRow("密码:", pwd_layout)

        # 手机输入
        self.phone_input = QLineEdit()
        self.phone_input.setMinimumWidth(300)
        self.phone_input.setFixedHeight(30)
        self.phone_input.setPlaceholderText("请输入手机号码（可选）")
        form_layout.addRow("手机:", self.phone_input)

        # 邮箱输入
        self.email_input = QLineEdit()
        self.email_input.setMinimumWidth(300)
        self.email_input.setFixedHeight(36)
        self.email_input.setPlaceholderText("请输入邮箱（可选）")
        form_layout.addRow("邮箱:", self.email_input)

        # 网站输入
        self.url_input = QLineEdit()
        self.url_input.setMinimumWidth(300)
        self.url_input.setFixedHeight(30)
        self.url_input.setPlaceholderText("请输入网站地址（可选）")
        form_layout.addRow("网站:", self.url_input)

        # 备注输入
        self.desc_input = QTextEdit()
        self.desc_input.setMinimumWidth(300)
        self.desc_input.setMinimumHeight(120)  # 优化备注框高度
        self.desc_input.setPlaceholderText("请输入备注信息（可选）")
        self.desc_input.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        form_layout.addRow("备注:", self.desc_input)

        layout.addLayout(form_layout)

        # 按钮布局
        button_layout = QHBoxLayout()
        button_layout.setSpacing(15)
        button_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 确认按钮
        self.confirm_button = QPushButton("确认添加")
        self.confirm_button.setObjectName("confirm_button")
        self.confirm_button.setFixedSize(100, 36)
        button_layout.addWidget(self.confirm_button)

        # 取消按钮
        cancel_button = QPushButton("取消")
        cancel_button.setObjectName("cancel_button")
        cancel_button.setFixedSize(100, 36)
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        layout.addLayout(button_layout)
        self.setLayout(layout)

        # 如果是编辑模式，填充数据
        if edit_data:
            self._populate_data(edit_data)

    def _add_custom_role(self):
        """添加新类别"""
        new_role, ok = QInputDialog.getText(
            self, "新建类别", "请输入新类别名称:", QLineEdit.EchoMode.Normal
        )
        if ok and new_role.strip():
            if new_role not in self.roles:
                self.added_role.emit(new_role)
                self.role_combo.addItem(new_role)

    def _populate_data(self, data):
        """填充编辑数据"""
        index = self.role_combo.findText(data["role"])
        if index >= 0:
            self.role_combo.setCurrentIndex(index)
        self.userid_input.setText(data["userID"])
        self.password_input.setText(data["pwd"])
        self.phone_input.setText(data.get("phone", ""))
        self.email_input.setText(data.get("email", ""))
        self.url_input.setText(data.get("url", ""))
        self.desc_input.setText(data.get("desc", ""))

    def show_random_pwd_dialog(self):
        """显示随机密码生成对话框"""
        dialog = RandomPasswordDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.password_input.setText(dialog.get_password())

    def get_password_data(self):
        """获取表单数据"""
        return {
            "id": date_util.timestamp_int(),
            "role": self.role_combo.currentText(),
            "userID": self.userid_input.text().strip(),
            "pwd": self.password_input.text().strip(),
            "phone": self.phone_input.text().strip(),
            "email": self.email_input.text().strip(),
            "url": self.url_input.text().strip(),
            "desc": self.desc_input.toPlainText().strip(),
            "utime": date_util.timestamp_int(),
        }
