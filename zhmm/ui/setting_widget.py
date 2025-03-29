#!/usr/bin/env python3
# coding=utf-8
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QSpinBox, QCheckBox, QPushButton
from zhmm import config


class SettingWidget(QWidget):
    """设置界面组件"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)

        # 自动锁定时间设置
        self.lock_time_label = QLabel("自动锁定时间（分钟）:")
        self.lock_time_spinbox = QSpinBox()
        self.lock_time_spinbox.setRange(1, 60)
        self.lock_time_spinbox.setValue(config.get_lock_time())
        self.lock_time_spinbox.valueChanged.connect(config.save_lock_time)
        self.lock_time_spinbox.setMaximumWidth(200)
        
        # 主题设置
        self.dark_theme_checkbox = QCheckBox("启用深色主题(暂未实现)")

        # 更改OpenID
        self.change_openid_button = QPushButton("更改OpenID(暂未实现)")
        self.change_openid_button.setMaximumWidth(200)

        # 导入xlsx文件
        self.import_xlsx_button = QPushButton("导入xlsx文件(暂未实现)")
        self.import_xlsx_button.setMaximumWidth(200)

        # 下载xlsx模版
        self.download_xlsx_button = QPushButton("下载xlsx模版(暂未实现)")
        self.download_xlsx_button.setMaximumWidth(200)

        layout.addWidget(self.lock_time_label)
        layout.addWidget(self.lock_time_spinbox)
        layout.addWidget(self.dark_theme_checkbox)
        layout.addWidget(self.change_openid_button)
        layout.addWidget(self.import_xlsx_button)
        layout.addWidget(self.download_xlsx_button)


        layout.addStretch()