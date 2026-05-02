#!/usr/bin/env python3
# @Date: 2024-07-03
# @LastEditTime: 2024-07-03

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableView,
    QToolTip,
    QVBoxLayout,
    QWidget,
)

import zhmm
from zhmm.config.constants import ZhmmFileInfo
from zhmm.data.sm_data_manager import SmData
from zhmm.gui.password.add_dialog import AddPasswordDialog
from zhmm.gui.password.operations import PasswordOperations
from zhmm.gui.password.reveal_delegate import RevealColumnDelegate
from zhmm.gui.password.table_models import CustomProxyModel, PasswordTableModel
from zhmm.utils.log import logger


class PasswordWindow(QWidget):
    """密码管理界面"""

    def __init__(self, info: ZhmmFileInfo, parent=None):
        super().__init__(parent)
        self.info = info
        if "sm_data" not in info or not info["sm_data"]:
            self.gl_data = SmData()
        else:
            self.gl_data = info["sm_data"]
        self.gl_data.file_path = info["file_path"]

        # 创建操作管理器
        self.operations = PasswordOperations(self.gl_data)

        # 密码明文显示自动隐藏定时器：{record_id: QTimer}
        self._reveal_timers: dict[int, QTimer] = {}

        self.setup_ui()

    def setup_ui(self):
        """设置界面"""
        # 创建主布局
        main_layout = QVBoxLayout(self)

        # 创建搜索区域
        search_layout = QHBoxLayout()

        # 添加类别筛选下拉框
        self.ini_role_ui(search_layout)

        search_label = QLabel("搜索:")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入关键字搜索账号、网站、备注等")
        self.search_input.textChanged.connect(self.filter_passwords)
        QTimer.singleShot(0, self.search_input.setFocus)  # 延迟聚焦到密码输入框

        # 在搜索区域添加复选框
        self.show_all_checkbox = QCheckBox("仅显示搜索结果")
        self.show_all_checkbox.setChecked(True)
        self.show_all_checkbox.setToolTip(
            "勾选：仅显示匹配关键字的数据；未填写关键字时不显示任何数据。取消勾选：显示全部数据（仍受类别筛选影响）。"
        )
        self.show_all_checkbox.toggled.connect(self.toggle_show_all)

        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_input, 1)
        search_layout.addWidget(self.show_all_checkbox)  # 新增复选框

        main_layout.addLayout(search_layout)

        status_layout = QHBoxLayout()
        # 添加状态标签（在表格下方）
        self.status_label = QLabel()
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("color: #666; font-size: 12px;")
        status_layout.addWidget(self.status_label)

        self.setup_ui_button(status_layout)
        main_layout.addLayout(status_layout)

        # 创建表格视图
        self.table_view = QTableView()
        self.table_model = PasswordTableModel(self.gl_data.mm["data"])

        # 设置选择模式（新增这两行）
        self.table_view.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table_view.setSelectionMode(QTableView.SelectionMode.SingleSelection)

        # 创建代理模型用于过滤（替换为自定义代理模型）
        self.proxy_model = CustomProxyModel()
        self.proxy_model.setSourceModel(self.table_model)
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.proxy_model.setFilterKeyColumn(-1)  # -1 表示搜索所有列

        self.table_view.setModel(self.proxy_model)
        # 默认显示密码列（掩码呈现由 model 层控制）
        self.table_view.setColumnHidden(3, False)

        # 安装“显示”列委托：用 SVG 眼睛图标代替文本
        self._reveal_delegate = RevealColumnDelegate(self.table_view, icon_size=18)
        self.table_view.setItemDelegateForColumn(PasswordTableModel.reveal_column(), self._reveal_delegate)

        # 新增单元格点击事件处理
        self.table_view.clicked.connect(self.on_table_cell_clicked)

        # 新增双击事件处理
        self.table_view.doubleClicked.connect(self.edit_selected_password)

        self.table_view.setAlternatingRowColors(True)
        self.table_view.setSortingEnabled(True)

        # 设置自适应列宽策略（新增以下三行）
        header = self.table_view.horizontalHeader()
        if header:
            # 获取表格字体度量
            font_metrics = self.table_view.fontMetrics()

            # 计算列宽方法
            def calculate_column_width(string, margin=8):
                # 计算内容最大宽度
                content_width = font_metrics.boundingRect(string).width()
                return content_width + margin

            header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)

            # 固定列宽度
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
            header.resizeSection(0, calculate_column_width("8888888888"))
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
            header.resizeSection(1, calculate_column_width("个人个人"))
            header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
            header.resizeSection(5, calculate_column_width("+86888888888888"))
            header.setSectionResizeMode(9, QHeaderView.ResizeMode.Fixed)
            header.resizeSection(9, calculate_column_width("8888888888"))
            # “显示”列：固定窄列，容纳一个 SVG 眼睛图标
            header.setSectionResizeMode(PasswordTableModel.reveal_column(), QHeaderView.ResizeMode.Fixed)
            header.resizeSection(PasswordTableModel.reveal_column(), RevealColumnDelegate.hint_column_width())

        main_layout.addWidget(self.table_view)

        # 初始化一次状态提示
        self.filter_passwords()

    def setup_ui_button(self, main_layout):
        # 创建按钮区域
        button_layout = QHBoxLayout()

        # 新增删除按钮
        delete_button = QPushButton("删除")
        delete_button.setMaximumWidth(128)
        delete_button.clicked.connect(self.delete_selected_password)

        add_button = QPushButton("添加")
        add_button.setMaximumWidth(128)
        add_button.clicked.connect(self.add_password)

        button_layout.addStretch()
        button_layout.addWidget(delete_button)
        button_layout.addWidget(add_button)

        main_layout.addLayout(button_layout)

    def ini_role_ui(self, search_layout):  # 添加类别筛选下拉框
        role_filter_label = QLabel("类别:")
        self.role_filter_combo = QComboBox()
        self.reset_roles_option()
        self.role_filter_combo.currentIndexChanged.connect(self.filter_role)

        # 设置下拉框最小宽度
        self.role_filter_combo.setMinimumWidth(100)
        # 设置下拉列表视图的宽度自适应内容
        self.role_filter_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)

        search_layout.addWidget(role_filter_label)
        search_layout.addWidget(self.role_filter_combo)
        pass

    def reset_roles_option(self):
        self.role_filter_combo.clear()
        self.role_filter_combo.addItem("全部", "")  # 添加一个默认选项
        if self.gl_data.mm and "roles" in self.gl_data.mm:
            roles = self.gl_data.mm["roles"]
            if roles is not None:
                for role in roles:
                    self.role_filter_combo.addItem(role, role)
        pass

    def filter_role(self):
        # 获取选中的角色
        selected_role = self.role_filter_combo.currentData()

        # 设置角色过滤
        self.proxy_model.use_role_filter = bool(selected_role)  # 如果有选中角色则启用角色过滤
        self.proxy_model.filter_role = selected_role  # 设置过滤的角色值

        # 触发过滤刷新
        self.filter_passwords()

    def filter_passwords(self):
        """过滤密码列表"""
        search_text = self.search_input.text()

        # 设置通配符过滤
        self.proxy_model.setFilterFixedString(search_text)

        # 状态提示：根据复选框与关键字内容更新
        if self.show_all_checkbox.isChecked():
            # 仅显示搜索结果
            if not self.proxy_model._has_filter:
                self.status_label.setText("请输入关键字以显示结果")
            else:
                self.status_label.setText(f"已按“{search_text}”筛选")
        else:
            # 显示全部数据（仍受类别筛选影响）
            self.status_label.setText("显示全部数据")

    def toggle_show_all(self, checked):
        """复选框状态切换处理"""
        self.proxy_model.show_all_data = not checked
        # 触发过滤刷新
        self.filter_passwords()

    def add_password(self):
        """添加密码"""
        roles = self.gl_data.mm.get("roles") or []
        dialog = AddPasswordDialog(self, roles)
        dialog.confirm_button.clicked.connect(lambda: self.confirm_add_password(dialog))
        dialog.added_role.connect(lambda new_role: self.add_role(new_role))
        dialog.exec()

    def add_role(self, new_role):
        """添加新角色"""
        if self.operations.add_role(new_role):
            self.reset_roles_option()

    def confirm_add_password(self, dialog):
        """确认添加密码"""
        password_data = dialog.get_password_data()

        # 使用操作管理器添加
        success, message = self.operations.add_password(password_data)

        if success:
            # 更新表格模型
            self.table_model.setZhData(self.gl_data.mm["data"])
            QMessageBox.information(dialog, "成功", message)
            dialog.accept()
        else:
            QMessageBox.warning(dialog, "警告" if "不能为空" in message else "错误", message)

    def export_passwords(self):
        """导出密码列表（待给外部调用）。"""
        from zhmm.gui.settings.import_export_handlers import (
            ImportExportHandlers,
        )

        handlers = ImportExportHandlers(self, self.info)
        handlers.export_passwords()

    def refresh_data(self):
        """刷新数据"""
        self.table_model.setZhData(self.gl_data.mm["data"])

    def delete_selected_password(self):
        """删除选中的密码项"""
        selected = self.table_view.selectionModel().selectedRows()  # type: ignore
        if not selected:
            QMessageBox.warning(self, "警告", "请先选择要删除的项目")
            return

        # 获取代理模型索引并转换为源模型索引
        proxy_index = selected[0]
        source_index = self.proxy_model.mapToSource(proxy_index)
        row = source_index.row()

        # 确认删除
        reply = QMessageBox.question(
            self,
            "确认删除",
            "确定要删除该账号记录吗？此操作不可恢复！",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            success, message = self.operations.delete_password(row)
            if success:
                # 更新表格
                self.table_model.setZhData(self.gl_data.mm["data"])
            else:
                QMessageBox.critical(self, "错误", message)

    def edit_selected_password(self):
        """编辑选中的密码项"""
        selected = self.table_view.selectionModel().selectedRows()  # type: ignore
        if not selected:
            QMessageBox.warning(self, "警告", "请先选择要编辑的项目")
            return

        # 获取源模型数据
        proxy_index = selected[0]
        source_index = self.proxy_model.mapToSource(proxy_index)
        row = source_index.row()
        edit_data = self.gl_data.mm["data"][row]

        # 创建编辑对话框并传入数据
        roles = self.gl_data.mm.get("roles") or []
        dialog = AddPasswordDialog(self, roles, edit_data=edit_data)
        dialog.confirm_button.clicked.connect(lambda: self._process_edit_result(dialog, row))
        dialog.added_role.connect(lambda new_role: self.add_role(new_role))
        dialog.setWindowTitle("编辑账号信息")
        dialog.confirm_button.setText("确认修改")
        dialog.exec()

    def _process_edit_result(self, dialog, original_row):
        """处理编辑结果"""
        new_data = dialog.get_password_data()

        # 使用操作管理器更新
        success, message = self.operations.update_password(original_row, new_data)

        if success:
            self.table_model.setZhData(self.gl_data.mm["data"])
            QMessageBox.information(dialog, "成功", message)
            dialog.accept()
        else:
            QMessageBox.warning(dialog, "警告" if "不能为空" in message else "错误", message)

    def confirm_modify_password(self, dialog):
        """确认添加密码"""
        password_data = dialog.get_password_data()

        # 验证必填字段
        if not password_data["userID"] or not password_data["pwd"]:
            QMessageBox.warning(dialog, "警告", "账号和密码不能为空")
            return

        # 添加到数据模型
        try:
            # 使用gl_data添加数据
            self.gl_data.add(password_data)
            if self.save():
                # 更新表格模型
                self.table_model.setZhData(self.gl_data.mm["data"])
                QMessageBox.information(dialog, "成功", "账号密码添加成功")
                dialog.accept()
            else:
                QMessageBox.critical(dialog, "错误", "添加失败，无法保存数据")
        except Exception as e:
            logger.error(f"添加密码出错: {str(e)}")
            QMessageBox.critical(dialog, "错误", f"添加出错: {str(e)}")

    def copy_cell_to_clipboard(self, index):
        """复制单元格内容到剪贴板（仅限“密码”列）"""
        if not index.isValid():
            return
        # 仅在点击“密码”列（索引3）时触发复制
        if index.column() != PasswordTableModel.password_column():
            return
        # 用 EditRole 取真实明文，避免复制到掩码占位符
        text = self.proxy_model.data(index, Qt.ItemDataRole.EditRole)
        if not text:
            return
        QApplication.clipboard().setText(str(text))  # type: ignore

        # 1) 鼠标位置气泡提示（最显眼）
        QToolTip.showText(QCursor.pos(), "✅ 已复制密码到剪贴板", self.table_view)

        # 2) 状态标签高亮提示（绿色加粗）
        self.status_label.setText("✅ 已复制密码到剪贴板（10 秒后自动清空）")
        self.status_label.setStyleSheet("color: #2e7d32; font-size: 13px; font-weight: bold;")

        def _reset_status_label() -> None:
            self.status_label.setText("")
            self.status_label.setStyleSheet("color: #666; font-size: 12px;")

        # 定时清空剪贴板，避免残留敏感信息
        QTimer.singleShot(10000, lambda: QApplication.clipboard().clear())  # type: ignore
        QTimer.singleShot(2500, _reset_status_label)

    # ------------------------------------------------------------------
    # 密码明文显示切换
    # ------------------------------------------------------------------
    def on_table_cell_clicked(self, index) -> None:
        """统一处理密码列 / “显示”列的点击行为。"""
        if not index.isValid():
            return
        col = index.column()
        if col == PasswordTableModel.reveal_column():
            self._toggle_reveal_at(index)
        elif col == PasswordTableModel.password_column():
            self.copy_cell_to_clipboard(index)

    def _toggle_reveal_at(self, proxy_index) -> None:
        """切换点击行的密码明文显示，并安排/重置自动隐藏定时器。"""
        source_index = self.proxy_model.mapToSource(proxy_index)
        source_row = source_index.row()
        rid = self.table_model.row_id(source_row)
        if rid is None:
            return
        revealed = self.table_model.toggle_revealed(source_row)
        # 已有定时器先停掉
        existing = self._reveal_timers.pop(rid, None)
        if existing is not None:
            existing.stop()
            existing.deleteLater()
        if revealed:
            duration = max(1, int(zhmm.config.get_password_reveal_duration()))
            timer = QTimer(self)
            timer.setSingleShot(True)
            timer.timeout.connect(lambda _rid=rid: self._auto_hide_reveal(_rid))
            timer.start(duration * 1000)
            self._reveal_timers[rid] = timer
            self._show_status(f"👁 密码已显示，{duration} 秒后自动隐藏", highlight=True)
        else:
            self._show_status("🔒 密码已隐藏", highlight=False)

    def _auto_hide_reveal(self, rid: int) -> None:
        """到期自动隐藏指定行的密码。"""
        self._reveal_timers.pop(rid, None)
        source_row = self.table_model.row_by_id(rid)
        if source_row < 0:
            return
        if self.table_model.is_revealed(source_row):
            self.table_model.set_revealed(source_row, False)
            self._show_status("🔒 密码已自动隐藏", highlight=False)

    def _show_status(self, text: str, *, highlight: bool) -> None:
        """状态栏闪提示，2.5 秒后息灭。"""
        self.status_label.setText(text)
        if highlight:
            self.status_label.setStyleSheet("color: #c62828; font-size: 13px; font-weight: bold;")
        else:
            self.status_label.setStyleSheet("color: #666; font-size: 12px;")

        def _reset() -> None:
            # 如果期间文案变了则不覆盖
            if self.status_label.text() == text:
                self.status_label.setText("")
                self.status_label.setStyleSheet("color: #666; font-size: 12px;")

        QTimer.singleShot(2500, _reset)

    def save(self):
        """保存数据"""
        return self.operations.save()
