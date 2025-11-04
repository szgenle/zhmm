#!/usr/bin/env python3
# coding=utf-8
from PyQt6.QtWidgets import (QDialog, QDialogButtonBox, QFormLayout, QLabel,
                             QLineEdit, QMessageBox, QVBoxLayout)


class ChangeOpenIdDialog(QDialog):
    """更改OpenID对话框"""

    def __init__(self, current_openid: str = "", parent=None):
        super().__init__(parent)
        self.current_openid = current_openid
        self.new_openid = ""
        self.setWindowTitle("更改OpenID")
        self.setFixedSize(400, 200)
        self.init_ui()

    def init_ui(self):
        """初始化界面"""
        main_layout = QVBoxLayout(self)

        # 说明标签
        info_label = QLabel("请输入新的OpenID（微信小程序中显示的OpenId）")
        info_label.setWordWrap(True)
        main_layout.addWidget(info_label)

        # 表单布局
        form_layout = QFormLayout()

        # 当前OpenID（只读显示）
        current_openid_label = QLabel(self.current_openid or "未设置")
        current_openid_label.setStyleSheet("color: gray;")
        form_layout.addRow("当前OpenID:", current_openid_label)

        # 新OpenID输入
        self.new_openid_edit = QLineEdit()
        self.new_openid_edit.setPlaceholderText("请输入新的OpenID")
        form_layout.addRow("新OpenID:", self.new_openid_edit)

        main_layout.addLayout(form_layout)

        # 对话框按钮
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.validate_and_accept)
        button_box.rejected.connect(self.reject)
        main_layout.addWidget(button_box)

    def validate_and_accept(self):
        """验证输入并确认"""
        new_openid = self.new_openid_edit.text().strip()

        if not new_openid:
            QMessageBox.warning(self, "警告", "OpenID不能为空")
            return

        if new_openid == self.current_openid:
            QMessageBox.information(self, "提示", "新OpenID与当前OpenID相同，无需更改")
            return

        self.new_openid = new_openid
        self.accept()

    def get_new_openid(self) -> str:
        """获取新的OpenID"""
        return self.new_openid
