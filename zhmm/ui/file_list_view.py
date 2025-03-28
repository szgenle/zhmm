#!/usr/bin/env python3
# coding=utf-8
# @Date: 2024-07-03
# @LastEditTime: 2024-07-03
from typing import TypedDict, Optional

from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QHBoxLayout, QTableWidget, QHeaderView, QFileDialog, \
    QTableWidgetItem, QMenu

from zhmm.ui.login_dialog import LoginDialog, ZhmmFileInfo
from zhmm.utils import file_util


class FileListWidget(QWidget):
    """文件列表组件"""
    login_success = pyqtSignal(dict)  # 登录成功信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        """设置界面"""
        main_layout = QVBoxLayout(self)
        
        # 文件列表表格
        self.file_table = QTableWidget()
        self.file_table.setColumnCount(3)  # 增加OpenID列
        self.file_table.setHorizontalHeaderLabels(['文件名', '文件路径', 'OpenID'])
        self.file_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # type: ignore
        self.file_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.file_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)  # 启用右键菜单
        self.file_table.customContextMenuRequested.connect(self.show_context_menu)
        self.file_table.itemClicked.connect(self.handle_item_click)

        # 设置选择模式（新增这两行）
        self.file_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.file_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)

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
        self.load_saved_files()

        QTimer.singleShot(0, self.auto_select_last_file)  # 延迟聚焦到密码输入框

    def auto_select_last_file(self):
        if self.file_table.rowCount() == 0:
            return
        
        # 自动选择第一行
        self.file_table.setCurrentCell(0, 0)
        self.file_table.setFocus()
        
        # 延迟触发点击事件（确保界面渲染完成）
        QTimer.singleShot(100, self.trigger_auto_login)

    def trigger_auto_login(self):
        """触发自动登录"""
        if not self.isActiveWindow():
            return
        if self.file_table.rowCount() > 0:
            item = self.file_table.item(0, 1)  # 获取文件路径对应的item
            self.handle_item_click(item)
        
        # 确保滚动到选中行可见（如果表格内容较多）
        item = self.file_table.item(0, 0)
        if item:
            self.file_table.scrollToItem(item)

    def select_files(self):
        """选择文件并更新表格"""
        file_path, _ = QFileDialog.getOpenFileName(self, '选择文件')
        if file_path:
            self.show_login_dialog(file_path)
        
    def show_login_dialog(self, file_path: str, openid: str | None = None):
        """显示登录对话框"""
        login_dialog = LoginDialog(file_path, openid)
        login_dialog.login_success.connect(lambda info: self.on_login_success(info))
        login_dialog.exec()

    def on_login_success(self, info: ZhmmFileInfo):
        """登录成功后的处理"""
        self.save_file_path_and_openid(info)
        self.login_success.emit(info)

    def save_file_path_and_openid(self, file_info: ZhmmFileInfo):
        """保存文件信息"""
        saved_files = self.load_all_saved_files()
        saved_files[file_info['file_path']] = {
            "openid": file_info['openid'],
            "filename": file_info['file_path'].split('/')[-1]
        }
        self.save_all_saved_files(saved_files)
        
        # 更新表格显示
        self.add_file_path(file_info['file_path'], file_info['openid'])

    def add_file_path(self, file_path, openid=None):
        if not file_path:
            return
        row = self.file_table.rowCount()
        self.file_table.insertRow(row)
        self.file_table.setItem(row, 0, QTableWidgetItem(file_path.split('/')[-1]))
        self.file_table.setItem(row, 1, QTableWidgetItem(file_path))
        self.file_table.setItem(row, 2, QTableWidgetItem(openid or ""))

    def load_saved_files(self):
        """加载已保存文件"""
        saved_files = self.load_all_saved_files()
        for file_path, info in saved_files.items():
            self.add_file_path(file_path, info['openid'])

    def load_all_saved_files(self) -> dict:
        """从文件加载所有保存记录"""
        files = file_util.load_json(self._get_storage_path())
        if not files:
            return {}
        return files

    def save_all_saved_files(self, file_infos):
        file_util.save_json(self._get_storage_path(), file_infos)

    def _get_storage_path(self):
        """获取存储文件路径"""
        return file_util.get_full_path(".zhmm_files.json").as_posix()

    def show_context_menu(self, pos):
        """显示右键菜单"""
        menu = QMenu()
        delete_action = menu.addAction("删除")
        if delete_action:
            delete_action.triggered.connect(self.delete_selected_item)
            menu.exec(self.file_table.viewport().mapToGlobal(pos))         # type: ignore

    def delete_selected_item(self):
        """删除选中项"""
        row = self.file_table.currentRow()
        if row >= 0:
            file_path = self.file_table.item(row, 1).text()         # type: ignore
            saved_files = self.load_all_saved_files()
            if file_path in saved_files:
                del saved_files[file_path]
                self.save_all_saved_files(saved_files)
            self.file_table.removeRow(row)

    def handle_item_click(self, item):
        """处理表格项点击"""
        row = item.row()
        file_path = self.file_table.item(row, 1).text()         # type: ignore
        openid = self.file_table.item(row, 2).text()            # type: ignore
        self.show_login_dialog(file_path, openid)               # type: ignore