#!/usr/bin/env python3
# coding=utf-8
# @Date: 2024-07-03
# @LastEditTime: 2024-07-03
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame, QPushButton, QHBoxLayout


class WelcomeWidget(QWidget):
    """欢迎界面组件"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        """设置界面"""
        main_layout = QVBoxLayout(self)

        # 欢迎标题
        welcome_label = QLabel("欢迎使用密码管理器")
        welcome_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome_label.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        main_layout.addWidget(welcome_label)

        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        main_layout.addWidget(line)

        # 说明文本
        info_label = QLabel("这是一个安全的密码管理工具，可以帮助您管理各种账号密码。")
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_label.setWordWrap(True)
        main_layout.addWidget(info_label)

        # 添加一些间距
        main_layout.addSpacing(20)

        # 登录按钮
        self.login_button = QPushButton("登录")
        self.login_button.setFixedWidth(120)
        self.login_button.setFixedHeight(40)

        # 功能区域（包含登录按钮）
        feature_layout = QHBoxLayout()
        feature_layout.addStretch()
        feature_layout.addWidget(self.login_button)
        feature_layout.addStretch()
        main_layout.addLayout(feature_layout)
