#!/usr/bin/env python3
# coding=utf-8
# @Date: 2024-07-03
# @LastEditTime: 2024-07-03
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QTabWidget)
from zhmm.ui.setting_widget import SettingWidget

from zhmm.ui.login_dialog import ZhmmFileInfo
from zhmm.ui_password import PasswordManagerWidget


class MainWindow(QWidget):
    """主窗口"""

    data_manager_widget: PasswordManagerWidget | None = None

    def __init__(self, info: ZhmmFileInfo):
        super().__init__()
        self.data_manager_widget = PasswordManagerWidget(info)
        self.setting_widget = SettingWidget()
        self.setup_ui()

    def setup_ui(self):
        # 创建标签容器
        tab_widget = QTabWidget()
        
        # 创建主布局
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(tab_widget)

        # 添加标签页
        tab_widget.addTab(self.data_manager_widget, "账号管理")
        tab_widget.addTab(self.setting_widget, "系统设置")