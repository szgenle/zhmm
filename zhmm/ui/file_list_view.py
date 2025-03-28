#!/usr/bin/env python3
# coding=utf-8
# @Date: 2024-07-03
# @LastEditTime: 2024-07-03
from typing import TypedDict

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QHBoxLayout, QTableWidget, QHeaderView, QFileDialog, \
    QTableWidgetItem

from zhmm.ui.login_dialog import LoginDialog, ZhmmFileInfo


class FileListWidget(QWidget):
    """文件列表组件"""
    login_success = pyqtSignal(ZhmmFileInfo)  # 登录成功信号
    
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
            self.show_login_dialog(file_path)
        
    def show_login_dialog(self, file_path):
        """显示登录对话框"""
        login_dialog = LoginDialog(file_path)
        login_dialog.login_success.connect(self.on_login_success)
        login_dialog.exec()

    def on_login_success(self, info: ZhmmFileInfo):
        """登录成功后的处理"""
        self.save_file_path_and_openid(info)
        self.login_success.emit(info)

    def save_file_path_and_openid(self, file_info: ZhmmFileInfo):
        """保存文件信息"""
        

    def add_file_path(self, file_path):
        if not file_path:
            return
        row = self.file_table.rowCount()
        self.file_table.insertRow(row)
        self.file_table.setItem(row, 0, QTableWidgetItem(file_path.split('/')[-1]))
        self.file_table.setItem(row, 1, QTableWidgetItem(file_path))