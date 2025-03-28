#!/usr/bin/env python3
# coding=utf-8
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTableWidget, QHeaderView

from zhmm.ui.login_dialog import ZhmmFileInfo


class DataManagerWidget(QWidget):
    """数据管理界面"""

    def __init__(self, info: ZhmmFileInfo, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        """初始化界面"""
        layout = QVBoxLayout()
        
        # 标题
        title_label = QLabel("密码数据管理")
        title_label.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(title_label)

        # 数据表格
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["网站", "用户名", "密码"])
        header = self.table.horizontalHeader()
        if header:
            header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)

        self.setLayout(layout)