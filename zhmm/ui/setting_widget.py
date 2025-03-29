#!/usr/bin/env python3
# coding=utf-8
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QSpinBox, QCheckBox


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
        self.lock_time_spinbox.setValue(5)
        
        # 主题设置
        self.dark_theme_checkbox = QCheckBox("启用深色主题")

        layout.addWidget(self.lock_time_label)
        layout.addWidget(self.lock_time_spinbox)
        layout.addWidget(self.dark_theme_checkbox)
        layout.addStretch()