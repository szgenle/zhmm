#!/usr/bin/env python3
# coding=utf-8
# @Date: 2024-07-03
# @LastEditTime: 2024-07-03
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QHBoxLayout, QTableWidget, QHeaderView, QFileDialog, \
    QTableWidgetItem


class FileListWidget(QWidget):
    """文件列表组件"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        """设置界面"""
        main_layout = QVBoxLayout(self)
        
        # 文件列表表格
        self.file_table = QTableWidget()
        self.file_table.setColumnCount(2)
        self.file_table.setHorizontalHeaderLabels(['文件名', '文件路径'])
        self.file_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch) # type: ignore
        self.file_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        main_layout.addWidget(self.file_table)

        # 添加文件选择按钮
        self.select_button = QPushButton('打开文件')
        self.select_button.clicked.connect(self.select_files)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self.select_button)
        button_layout.addStretch()
        main_layout.addLayout(button_layout)

    def select_files(self):
        """选择文件并更新表格"""
        file_path, _ = QFileDialog.getOpenFileName(self, '选择文件')
        if file_path:
            row = self.file_table.rowCount()
            self.file_table.insertRow(row)
            self.file_table.setItem(row, 0, QTableWidgetItem(file_path.split('/')[-1]))
            self.file_table.setItem(row, 1, QTableWidgetItem(file_path))