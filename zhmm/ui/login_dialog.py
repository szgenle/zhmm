#!/usr/bin/env python3
# coding=utf-8
# @Date: 2024-07-03
# @LastEditTime: 2024-07-03
import json
from typing import TypedDict, Optional

from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox, QGridLayout)

from zhmm import sm_util, sm_data
from zhmm.qt_components.dialog import Dialog
from zhmm.sm_data import SmData
from zhmm.utils import data_conversion
from zhmm.utils.log import logger


class ZhmmFileInfo(TypedDict):
    file_path: str
    openid: str
    sm_data: Optional[SmData | None]


class LoginDialog(Dialog):
    """登录对话框"""
    login_success = pyqtSignal(dict)  # 保持信号声明不变

    def __init__(self, content: str, openid: str | None = None, parent=None):
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

        row = 0
        # OpenID输入
        openid_label = QLabel("OpenID:")
        self.openid_input = QLineEdit()
        self.openid_input.setPlaceholderText("请输入微信小程序中显示的OpenId")
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
        self.password_input.setPlaceholderText("请输入密码")

        form_layout.addWidget(password_label, row, 0)
        form_layout.addWidget(self.password_input, row, 1)

        layout.addLayout(form_layout)

        # 添加一些间距
        layout.addSpacing(20)

        # 按钮布局
        button_layout = QHBoxLayout()

        # 登录按钮
        self.login_button = QPushButton("登录")
        self.login_button.clicked.connect(lambda: self.verify_login(content))
        button_layout.addWidget(self.login_button)

        # 取消按钮
        cancel_button = QPushButton("取消")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        layout.addLayout(button_layout)

        self.setLayout(layout)

    def verify_login(self, content: str):
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
            pwd = sm_util.hash_by_sm3(data_conversion.chars_to_bytes(pwd_suffix))

            smdata = sm_data.SmData()
            smdata.init(openid, pwd)

            if content == '':
                user_mm_data = {
                    'userID': openid,
                    'pwd': password,
                    'url': 'szgenle',
                    'desc': '务必记住当前的userID和密码'
                }
                smdata.add_with_dict(user_mm_data)
            else:
                decrypt_result = smdata.decrypt(content)

                if not decrypt_result or not decrypt_result['res']:
                    if self.openid_input.isHidden():
                        QMessageBox.critical(self, "错误", "密码不正确")
                    else:
                        QMessageBox.critical(self, "错误", "OpenID或者密码不正确")
                    self.password_input.clear()  # 新增：清空密码输入框
                    return

                user_mm_data = json.loads(decrypt_result['res'])
                smdata.set_mm(user_mm_data)

            # 登录成功
            logger.info(f"用户 {openid} 登录成功")
            # 登录成功时需要显式指定字典类型
            info = {
                'openid': openid,
                'sm_data': smdata
            }
            
            self.login_success.emit(info)  # 直接传递强类型对象
            self.accept()

        except Exception as e:
            logger.error(f"登录验证出错: {str(e)}")
            QMessageBox.critical(self, "错误", f"登录验证出错: {str(e)}")
            self.password_input.clear()  # 新增：异常情况下清空
