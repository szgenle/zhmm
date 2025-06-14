#!/usr/bin/env python3
# coding=utf-8
# @Date: 2024-07-03
# @LastEditTime: 2024-07-03
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QTabWidget)
from zhmm.window_setting.setting_window import SettingWindow

from zhmm.ui_defined import ZhmmFileInfo
from zhmm.ui_password import PasswordManagerWidget


class MainWindow(QWidget):
    """主窗口"""

    data_manager_widget: PasswordManagerWidget | None = None

    def __init__(self, info: ZhmmFileInfo):
        super().__init__()
        self.data_manager_widget = PasswordManagerWidget(info)
        self.setting_widget = SettingWindow(info)
        self.setting_widget.imported_xlsx.connect(self.imported_xlsx_data)
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

    def imported_xlsx_data(self):
        if self.data_manager_widget:
            self.data_manager_widget.refresh_data()