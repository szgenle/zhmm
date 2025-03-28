#!/usr/bin/env python3
# coding=utf-8
# @Date: 2024-07-03
# @LastEditTime: 2024-07-03

import json
from PyQt6.QtCore import Qt, pyqtSignal, QSortFilterProxyModel, QAbstractTableModel
from PyQt6.QtGui import QFont, QIcon
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QTableView, QHeaderView,
                             QMessageBox, QDialog, QGridLayout, QComboBox,
                             QFrame, QFormLayout, QFileDialog)

from zhmm.data_exporter import DataExporter
from zhmm.utils.log import logger


class PasswordTableModel(QAbstractTableModel):
    """密码表格数据模型"""

    def __init__(self, data=None):
        super().__init__()
        self.headers = ['ID', '类别', '账号', '密码', '手机', '邮箱', '网站', '备注', '更新时间']
        self.keys = ['id', 'role', 'userID', 'pwd', 'phone', 'email', 'url', 'desc', 'utime']
        self._data = data if data else []

    def rowCount(self, parent=None):
        return len(self._data)

    def columnCount(self, parent=None):
        return len(self.headers)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None

        if role == Qt.ItemDataRole.DisplayRole:
            row = index.row()
            col = index.column()
            item = self._data[row]
            key = self.keys[col]

            # 返回对应的数据，如果不存在则返回空字符串
            return str(item.get(key, ''))

        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return self.headers[section]
        return None

    def setZhData(self, data):
        self.beginResetModel()
        self._data = data
        self.endResetModel()


class AddPasswordDialog(QDialog):
    """添加密码对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("添加账号密码")
        self.setFixedSize(500, 400)

        # 创建布局
        layout = QVBoxLayout()

        # 标题标签
        title_label = QLabel("请输入账号密码信息")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        layout.addWidget(title_label)

        # 添加一些间距
        layout.addSpacing(20)

        # 创建表单布局
        form_layout = QFormLayout()

        # 类别选择
        self.role_combo = QComboBox()
        self.role_combo.addItems(["个人", "工作", "社交", "金融", "其他"])
        form_layout.addRow("类别:", self.role_combo)

        # 账号输入
        self.userid_input = QLineEdit()
        self.userid_input.setPlaceholderText("请输入账号")
        form_layout.addRow("账号:", self.userid_input)

        # 密码输入
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("请输入密码")
        form_layout.addRow("密码:", self.password_input)

        # 手机输入
        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("请输入手机号码（可选）")
        form_layout.addRow("手机:", self.phone_input)

        # 邮箱输入
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("请输入邮箱（可选）")
        form_layout.addRow("邮箱:", self.email_input)

        # 网站输入
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("请输入网站地址（可选）")
        form_layout.addRow("网站:", self.url_input)

        # 备注输入
        self.desc_input = QLineEdit()
        self.desc_input.setPlaceholderText("请输入备注信息（可选）")
        form_layout.addRow("备注:", self.desc_input)

        layout.addLayout(form_layout)

        # 添加一些间距
        layout.addSpacing(20)

        # 按钮布局
        button_layout = QHBoxLayout()

        # 确认按钮
        self.confirm_button = QPushButton("确认添加")
        button_layout.addWidget(self.confirm_button)

        # 取消按钮
        cancel_button = QPushButton("取消")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        layout.addLayout(button_layout)

        self.setLayout(layout)

    def get_password_data(self):
        """获取表单数据"""
        return {
            'role': self.role_combo.currentText(),
            'userID': self.userid_input.text().strip(),
            'pwd': self.password_input.text().strip(),
            'phone': self.phone_input.text().strip(),
            'email': self.email_input.text().strip(),
            'url': self.url_input.text().strip(),
            'desc': self.desc_input.text().strip()
        }


class PasswordManagerWidget(QWidget):
    """密码管理界面"""

    def __init__(self, gl_data, parent=None):
        super().__init__(parent)
        self.gl_data = gl_data
        self.setup_ui()

    def setup_ui(self):
        """设置界面"""
        # 创建主布局
        main_layout = QVBoxLayout(self)

        # 创建搜索区域
        search_layout = QHBoxLayout()

        search_label = QLabel("搜索:")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入关键字搜索账号、网站、备注等")
        self.search_input.textChanged.connect(self.filter_passwords)

        search_button = QPushButton("搜索")
        search_button.clicked.connect(self.filter_passwords)

        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_input, 1)  # 1表示伸展因子
        search_layout.addWidget(search_button)

        main_layout.addLayout(search_layout)

        # 创建表格视图
        self.table_view = QTableView()
        self.table_model = PasswordTableModel(self.gl_data.mm['data'])

        # 创建代理模型用于过滤
        self.proxy_model = QSortFilterProxyModel()
        self.proxy_model.setSourceModel(self.table_model)
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)

        self.table_view.setModel(self.proxy_model)

        # 设置表格属性
        header = self.table_view.horizontalHeader()
        if header:
            header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_view.setAlternatingRowColors(True)
        self.table_view.setSortingEnabled(True)

        main_layout.addWidget(self.table_view)

        # 创建按钮区域
        button_layout = QHBoxLayout()

        add_button = QPushButton("添加")
        add_button.clicked.connect(self.add_password)

        export_button = QPushButton("导出")
        export_button.clicked.connect(self.export_passwords)

        button_layout.addWidget(add_button)
        button_layout.addWidget(export_button)

        main_layout.addLayout(button_layout)

    def filter_passwords(self):
        """过滤密码列表"""
        search_text = self.search_input.text()
        # 设置过滤器，这里简单地对所有列进行过滤
        self.proxy_model.setFilterFixedString(search_text)

    def add_password(self):
        """添加密码"""
        dialog = AddPasswordDialog(self)
        dialog.confirm_button.clicked.connect(lambda: self.confirm_add_password(dialog))
        dialog.exec()

    def confirm_add_password(self, dialog):
        """确认添加密码"""
        password_data = dialog.get_password_data()

        # 验证必填字段
        if not password_data['userID'] or not password_data['pwd']:
            QMessageBox.warning(dialog, "警告", "账号和密码不能为空")
            return

        # 添加到数据模型
        try:
            # 使用gl_data添加数据
            file_path = 'zhmm.gl'  # 默认文件路径
            if self.gl_data.add(password_data, file_path):
                # 更新表格模型
                self.table_model.setZhData(self.gl_data.mm['data'])
                QMessageBox.information(dialog, "成功", "账号密码添加成功")
                dialog.accept()
            else:
                QMessageBox.critical(dialog, "错误", "添加失败，无法保存数据")
        except Exception as e:
            logger.error(f"添加密码出错: {str(e)}")
            QMessageBox.critical(dialog, "错误", f"添加出错: {str(e)}")

    def export_passwords(self):
        """导出密码列表"""
        DataExporter.export_to_file(self.gl_data.mm['data'])

    def refresh_data(self):
        """刷新数据"""
        self.table_model.setZhData(self.gl_data.mm['data'])
