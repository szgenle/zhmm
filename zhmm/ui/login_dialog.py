#!/usr/bin/env python3
# coding=utf-8
# @Date: 2024-07-03
# @LastEditTime: 2024-07-03
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox, QGridLayout)

from zhmm import sm_util, sm_data
from zhmm.qt_components.dialog import Dialog
from zhmm.utils import file_util, data_conversion
from zhmm.utils.log import logger


class LoginDialog(Dialog):
    """登录对话框"""
    login_success = pyqtSignal()  # 登录成功信号

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("登录验证")
        self.setFixedSize(400, 250)
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint)
        self.setModal(True)

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

        # OpenID输入
        openid_label = QLabel("OpenID:")
        self.openid_input = QLineEdit()
        self.openid_input.setPlaceholderText("请输入微信小程序中显示的OpenId")
        form_layout.addWidget(openid_label, 0, 0)
        form_layout.addWidget(self.openid_input, 0, 1)

        # 密码输入
        password_label = QLabel("密码:")
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("请输入密码")
        form_layout.addWidget(password_label, 1, 0)
        form_layout.addWidget(self.password_input, 1, 1)

        layout.addLayout(form_layout)

        # 添加一些间距
        layout.addSpacing(20)

        # 按钮布局
        button_layout = QHBoxLayout()

        # 登录按钮
        self.login_button = QPushButton("登录")
        self.login_button.clicked.connect(self.verify_login)
        button_layout.addWidget(self.login_button)

        # 取消按钮
        cancel_button = QPushButton("取消")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        layout.addLayout(button_layout)

        self.setLayout(layout)

    def verify_login(self):
        """验证登录信息"""
        openid = self.openid_input.text().strip()
        password = self.password_input.text().strip()

        if not openid:
            QMessageBox.warning(self, "警告", "OpenID不能为空")
            return

        if not password:
            QMessageBox.warning(self, "警告", "密码不能为空")
            return

        # 验证逻辑，使用现有的gl_data验证方法
        try:
            # 处理密码，与cmd_ui.py中相同的逻辑
            pwd_suffix = password + 'woie*#jk20kH2^D@U28)'
            pwd = sm_util.hash_by_sm3(data_conversion.string_to_bytes(pwd_suffix))

            gl_data1 = sm_data.SmData()
            gl_data1.init(openid, pwd)

            # 尝试读取并解密文件
            file_path = 'zhmm.gl'  # 默认文件路径
            data = file_util.get_file_content(file_path)

            if data:
                decrypt_result = gl_data1.decrypt(data)

                if not decrypt_result or not decrypt_result['res']:
                    QMessageBox.critical(self, "错误", "密码不正确")
                    return

                # 登录成功
                logger.info(f"用户 {openid} 登录成功")
                self.login_success.emit()
                self.accept()
            else:
                QMessageBox.critical(self, "错误", f"无法读取文件: {file_path}")

        except Exception as e:
            logger.error(f"登录验证出错: {str(e)}")
            QMessageBox.critical(self, "错误", f"登录验证出错: {str(e)}")
