#!/usr/bin/env python3
# @Date: 2024-07-03
# @LastEditTime: 2024-07-03
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

from zhmm.gui.file_list_widget import FileListWidget


class WelcomeWidget(QWidget):
    """欢迎界面组件"""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        """初始化界面组件及布局"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 40, 20, 20)  # 设置布局边距
        main_layout.setSpacing(25)  # 组件间距调整

        # 欢迎标题（调整字体和颜色）
        welcome_label = QLabel("欢迎使用账号小笨苯")
        welcome_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome_label.setStyleSheet("color: #2c3e50;")
        welcome_label.setFont(QFont("Arial", 28, QFont.Weight.ExtraBold))
        main_layout.addWidget(welcome_label)

        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        main_layout.addWidget(line)

        # 说明文本（增强可读性）
        info_label = QLabel("这是一个安全的账号管理工具，可以帮助您管理各种账号密码。\n" "请选择已有数据库文件或创建新文件开始使用。")
        info_label.setStyleSheet("color: #7f8c8d; font-size: 14px;")
        info_label.setFont(QFont("Arial", 12))
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_label.setWordWrap(True)
        main_layout.addWidget(info_label)

        # 文件列表组件（添加边距）
        self.file_list = FileListWidget()
        self.file_list.setContentsMargins(0, 15, 0, 15)
        main_layout.addWidget(self.file_list)
