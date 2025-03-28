#!/usr/bin/env python3
# coding=utf-8
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTableWidget, QHeaderView, QTableWidgetItem

from zhmm.sm_data import SmData


class DataManagerWidget(QWidget):
    """数据管理界面"""

    def __init__(self, info: SmData, parent=None):
        super().__init__(parent)
        self.info = info  # 保存数据实例
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
        self.table.setColumnCount(len(SmData.keys))
        self.table.setHorizontalHeaderLabels(SmData.heads)
        header = self.table.horizontalHeader()
        if header:
            header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)
        
        self.load_data()  # 新增数据加载
        self.setLayout(layout)

    def load_data(self):
        """加载数据到表格"""
        entries = self.info.mm['data']  # 假设SmData有获取所有条目的方法
        self.table.setRowCount(len(entries))
        
        for row, entry in enumerate(entries):
            for col, key in enumerate(SmData.keys):  # 遍历所有字段
                value = str(entry.get(key, ''))  # 安全获取字段值
                self.table.setItem(row, col, QTableWidgetItem(value))
            self.table.setRowHeight(row, 30)  # 设置行高更紧凑