#!/usr/bin/env python3
# @Date: 2024-07-03
# @LastEditTime: 2024-07-03
from datetime import datetime

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QMenu,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

import zhmm
from zhmm.config import saved_files as saved_files_store
from zhmm.config.constants import ZhmmFileInfo
from zhmm.gui.decrypt_data_view import UIDecryptData
from zhmm.gui.login.create_vault_dialog import CreateVaultDialog
from zhmm.gui.login.login_window import LoginWindow


class FileListWidget(QWidget):
    """文件列表组件"""

    login_success = pyqtSignal(dict)  # 登录成功信号

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        """设置界面"""
        self.setAcceptDrops(True)  # 新增：启用拖拽接受
        main_layout = QVBoxLayout(self)

        # 文件列表表格
        self.file_table = QTableWidget()
        self.file_table.setColumnCount(5)  # 文件名、文件路径、账号（隐藏）、密码、最近访问时间
        self.file_table.setHorizontalHeaderLabels(["文件名", "文件路径", "账号", "密码", "最近访问时间"])
        self.file_table.setColumnHidden(0, True)
        self.file_table.setColumnHidden(2, True)
        self.file_table.setColumnHidden(3, True)
        self.file_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # type: ignore
        self.file_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # type: ignore
        self.file_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.file_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)  # 启用右键菜单
        self.file_table.customContextMenuRequested.connect(self.show_context_menu)
        self.file_table.itemClicked.connect(self.handle_item_click)

        # 设置选择模式（新增这两行）
        self.file_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.file_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)

        main_layout.addWidget(self.file_table)

        # 添加文件选择按钮
        self.select_button = QPushButton("打开文件")
        self.select_button.clicked.connect(self.select_files)

        # 新增新建按钮
        self.new_button = QPushButton("新建账号小本本")
        self.new_button.clicked.connect(self.create_new_file)

        # 按钮布局
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self.new_button)
        button_layout.addWidget(self.select_button)
        button_layout.addStretch()
        main_layout.addLayout(button_layout)
        self.load_saved_files()

    def select_last_file(self):
        if self.file_table.rowCount() == 0:
            return

        # 自动选择第一行
        self.file_table.setCurrentCell(0, 0)
        self.file_table.setFocus()

        # 延迟触发点击事件（确保界面渲染完成）
        QTimer.singleShot(100, self.trigger_auto_login)

    def auto_select_last_file(self):
        QTimer.singleShot(0, self.select_last_file)  # 延迟聚焦到密码输入框

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
        file_path, _ = QFileDialog.getOpenFileName(self, "选择文件")
        if file_path:
            self.show_login_dialog(file_path)

    def show_login_dialog(self, file_path: str, account: str | None = None, hashpw: str | None = None):
        login_dialog = LoginWindow(account, hashpw)
        login_dialog.login_success.connect(lambda info: self.on_login_success(file_path, info))
        login_dialog.exec()

    def on_create_success(self, file_path: str, info: dict):
        import hashlib

        file_name = hashlib.md5(info["account"].encode("utf-8")).hexdigest()
        # 使用原始密码进行密钥派生（更安全）
        if zhmm.config.init(file_name, info["password"]) is False:
            QMessageBox.critical(self, "错误", "账号已存在，请输入正确的密码")
            return
        self.on_login_success(file_path, info)

    def on_login_success(self, file_path: str, info: dict):
        """登录成功后解密并加载文件。"""
        import hashlib

        file_name = hashlib.md5(info["account"].encode("utf-8")).hexdigest()
        if zhmm.config.init(file_name, info["password"]) is False:
            return

        decryptor = UIDecryptData()
        sm_data = decryptor.decrypt_file(file_path, info["account"], info["password"])
        if sm_data is None:
            QMessageBox.critical(self, "错误", "文件解密失败")
            return

        """登录成功后的处理"""
        # 构造文件信息字典，确保类型匹配
        # 使用类型断言确保 sm_data 是 SmData 类型
        from zhmm.data.sm_data_manager import SmData

        assert isinstance(sm_data, SmData)

        file_info: ZhmmFileInfo = {
            "file_path": file_path,
            "account": info["account"],
            "hashpw": info["hashpw"],
            "sm_data": sm_data,
        }
        self.save_file_path_and_account(file_info)
        self.login_success.emit(file_info)

    def save_file_path_and_account(self, file_info: ZhmmFileInfo):
        """保存文件信息"""
        saved_files = self.load_all_saved_files()
        saved_files[file_info["file_path"]] = {
            "account": file_info["account"],
            "hashpw": file_info["hashpw"],
            "filename": file_info["file_path"].split("/")[-1],
            "last_access_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        self.save_all_saved_files(saved_files)

        # 更新表格显示
        self.add_file_path(file_info["file_path"], file_info)

    def add_file_path(self, file_path, file_info):
        if not file_path or not file_info:
            return
        account = file_info.get("account")
        hashpw = file_info.get("hashpw")
        last_access_time = file_info.get("last_access_time")
        row = self.file_table.rowCount()
        self.file_table.insertRow(row)
        self.file_table.setItem(row, 0, QTableWidgetItem(file_path.split("/")[-1]))
        self.file_table.setItem(row, 1, QTableWidgetItem(file_path))
        self.file_table.setItem(row, 2, QTableWidgetItem(account or ""))
        self.file_table.setItem(row, 3, QTableWidgetItem(hashpw or ""))
        self.file_table.setItem(row, 4, QTableWidgetItem(last_access_time or ""))

    def load_saved_files(self):
        """加载已保存文件"""
        saved_files = self.load_all_saved_files()
        # 按照last_access_time倒序排序
        sorted_files = {}
        if saved_files:
            # 将字典转换为列表并按照last_access_time倒序排序
            sorted_items = sorted(
                saved_files.items(),
                key=lambda x: x[1].get("last_access_time", ""),
                reverse=True,  # 倒序排序，最近的日期排在前面
            )
            # 转回字典
            sorted_files = dict(sorted_items)

        # 添加到表格中
        for file_path, info in sorted_files.items():
            self.add_file_path(file_path, info)

    def load_all_saved_files(self) -> dict:
        """从文件加载所有保存记录（委托给 :mod:`zhmm.config.saved_files`）。"""
        return saved_files_store.load_all()

    def save_all_saved_files(self, file_infos):
        saved_files_store.save_all(file_infos)

    def _get_storage_path(self):
        """获取存储文件路径。"""
        return saved_files_store.get_storage_path()

    def show_context_menu(self, pos):
        """显示右键菜单"""
        menu = QMenu()
        delete_action = menu.addAction("删除")
        if delete_action:
            delete_action.triggered.connect(self.delete_selected_item)
            menu.exec(self.file_table.viewport().mapToGlobal(pos))  # type: ignore

    def delete_selected_item(self):
        """删除选中项"""
        row = self.file_table.currentRow()
        if row >= 0:
            file_path = self.file_table.item(row, 1).text()  # type: ignore
            saved_files = self.load_all_saved_files()
            if file_path in saved_files:
                del saved_files[file_path]
                self.save_all_saved_files(saved_files)
            self.file_table.removeRow(row)

    def handle_item_click(self, item):
        """处理表格项点击"""
        row = item.row()
        file_path = self.file_table.item(row, 1).text()  # type: ignore
        account = self.file_table.item(row, 2).text()  # type: ignore
        hashpw = self.file_table.item(row, 3).text()  # type: ignore
        self.show_login_dialog(file_path, account, hashpw)  # type: ignore

    # 新增以下两个方法实现拖拽功能
    def dragEnterEvent(self, event):  # type: ignore
        """拖拽进入事件处理"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):  # type: ignore
        """拖放事件处理"""
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path:
                self.show_login_dialog(file_path)
        event.acceptProposedAction()

    def create_new_file(self):
        """新建账号小本本（密码库）：弹出整合向导弹窗收集路径/账号/主密码。"""
        dialog = CreateVaultDialog(self)
        dialog.vault_create_requested.connect(lambda file_path, info: self.on_create_success(file_path, info))
        dialog.exec()
