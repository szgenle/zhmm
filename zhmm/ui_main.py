#!/usr/bin/env python3
# coding=utf-8
# @Date: 2024-07-03
# @LastEditTime: 2024-07-03
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QPushButton, QTabWidget, QVBoxLayout, QWidget

from zhmm.ui_defined import ZhmmFileInfo
from zhmm.window_password.password_window import PasswordWindow
from zhmm.window_setting.setting_window import SettingWindow


class MainWindow(QWidget):
    """主窗口"""

    return_requested = pyqtSignal()  # 返回首页的信号
    data_manager_widget: PasswordWindow | None = None

    def __init__(self, info: ZhmmFileInfo):
        super().__init__()
        self.data_manager_widget = PasswordWindow(info)
        self.setting_widget = SettingWindow(info)
        self.setting_widget.imported_xlsx.connect(self.imported_xlsx_data)
        self.setup_ui()

    def setup_ui(self):
        # 创建主布局
        main_layout = QVBoxLayout(self)

        # 创建标签容器
        tab_widget = QTabWidget()
        main_layout.addWidget(tab_widget)

        # 添加标签页
        tab_widget.addTab(self.data_manager_widget, "账号管理")
        tab_widget.addTab(self.setting_widget, "系统设置")

        # 创建返回按钮区域（放在最下方）
        button_layout = QHBoxLayout()
        return_btn = QPushButton("返回首页")
        return_btn.clicked.connect(self.return_requested.emit)
        button_layout.addWidget(return_btn)
        button_layout.addStretch()
        main_layout.addLayout(button_layout)

    def imported_xlsx_data(self):
        if self.data_manager_widget:
            self.data_manager_widget.refresh_data()
