#!/usr/bin/env python3
# @Date: 2024-07-03
# @LastEditTime: 2024-07-03

import re

from PyQt6.QtCore import Qt, QTimer, QUrl, pyqtSignal
from PyQt6.QtGui import QCursor, QDesktopServices
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QTableView,
    QToolTip,
    QVBoxLayout,
    QWidget,
)

import zhmm
from zhmm.config.constants import ZhmmFileInfo
from zhmm.core.errors import ValidationError
from zhmm.data.sm_data_manager import SmData
from zhmm.gui.password.add_dialog import AddPasswordDialog
from zhmm.gui.password.operations import PasswordOperations
from zhmm.gui.password.reveal_delegate import RevealColumnDelegate
from zhmm.gui.password.table_models import CustomProxyModel, PasswordTableModel
from zhmm.gui.texts import Status, Tooltip
from zhmm.utils.log import logger
from zhmm.widgets.combo_box import WideComboBox


class PasswordWindow(QWidget):
    """密码管理界面"""

    # 状态变更信号：(text, level)，level ∈ {'normal', 'highlight', 'success'}
    # 由外层 MainWindow 接收后统一渲染到窗口底部状态栏。
    status_changed = pyqtSignal(str, str)

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
        # 搜索防抖：连续输入时只在停顿 150ms 后触发一次过滤，
        # 避免逐字符刷新导致的 UI 抖动与不必要的全表扫描。
        self._search_debounce = QTimer(self)
        self._search_debounce.setSingleShot(True)
        self._search_debounce.setInterval(150)
        self._search_debounce.timeout.connect(self.filter_passwords)
        self.search_input.textChanged.connect(self._on_search_text_changed)
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

        # “添加”按钮与搜索同一行（最右侧），腾出窗口底部给状态栏
        self.setup_ui_button(search_layout)

        main_layout.addLayout(search_layout)

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

        # 右键上下文菜单
        self.table_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table_view.customContextMenuRequested.connect(self._show_context_menu)

        self.table_view.setAlternatingRowColors(True)
        self.table_view.setSortingEnabled(True)

        # 列宽策略：全部允许用户拖拽调整（Interactive），仅给出一个合理的初始宽度。
        # 之前常用的 ResizeToContents 会导致表头不能手动拖拽（站点被内容锁死）；
        # 同时备注这类长文本列会把整行凅到很宽，不利阅读。为此改为 Interactive +
        # 预设初始宽，备注也给个默认宽度（~220px），太长时用户自行拉宽。
        header = self.table_view.horizontalHeader()
        if header:
            # 表格字体度量，用于按内容估算初始宽度
            font_metrics = self.table_view.fontMetrics()

            def calculate_column_width(string: str, margin: int = 16) -> int:
                content_width = font_metrics.boundingRect(string).width()
                return content_width + margin

            # 默认全部可拖，不让最后一列自动撑满（避免更新时间列被拉得很宽）
            header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
            header.setStretchLastSection(False)

            # 各列初始宽度（按列索引，与 headers / keys 保持一致）
            # 0 ID
            header.resizeSection(0, calculate_column_width("8888888888"))
            # 1 类别
            header.resizeSection(1, calculate_column_width("个人个人个人"))
            # 2 账号
            header.resizeSection(2, calculate_column_width("account@example.com"))
            # 3 密码
            header.resizeSection(3, calculate_column_width("••••••••••••"))
            # 4 “显示”列：固定窄列（按图标宽度）
            header.resizeSection(PasswordTableModel.reveal_column(), RevealColumnDelegate.hint_column_width())
            # 5 动态码
            header.resizeSection(PasswordTableModel.totp_column(), calculate_column_width("888888  88s"))
            # 6 手机
            header.resizeSection(6, calculate_column_width("+86888888888888"))
            # 7 邮箱
            header.resizeSection(7, calculate_column_width("account@example.com"))
            # 8 网站
            header.resizeSection(8, calculate_column_width("https://auth.example.com"))
            # 9 备注：给个默认宽度，不够时用户自行拉宽
            header.resizeSection(9, 220)
            # 10 更新时间：按 YYYY-MM-DD 宽度
            header.resizeSection(10, calculate_column_width("2026-05-02"))

        main_layout.addWidget(self.table_view)

        # 窗口底部状态栏上移到 MainWindow（跟“返回首页”同一行），
        # 这里只负责 emit status_changed 信号。

        # 动态码列每 1 秒刷新（仅发 dataChanged，无需全表重绘）
        self._totp_refresh_timer = QTimer(self)
        self._totp_refresh_timer.setInterval(1000)
        self._totp_refresh_timer.timeout.connect(self._refresh_totp_column)
        self._totp_refresh_timer.start()

        # 初始化一次状态提示
        self.filter_passwords()

    def setup_ui_button(self, search_layout):
        """把“添加”按钮挂到搜索行最右侧，不再单独占一行。"""
        add_button = QPushButton("添加")
        add_button.setMaximumWidth(128)
        add_button.clicked.connect(self.add_password)

        search_layout.addWidget(add_button)

    def ini_role_ui(self, search_layout):  # 添加类别筛选下拉框
        role_filter_label = QLabel("类别:")
        self.role_filter_combo = WideComboBox()
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

    def _on_search_text_changed(self, _text: str = "") -> None:
        """搜索框文本变化：重启防抖定时器，等待用户停顿后再真正过滤。"""
        self._search_debounce.start()

    def filter_passwords(self):
        """过滤密码列表"""
        # 若因 show_all / 类别切换等直接调用，提前取消尚未触发的防抖
        if hasattr(self, "_search_debounce") and self._search_debounce.isActive():
            self._search_debounce.stop()
        search_text = self.search_input.text()

        # 设置通配符过滤
        self.proxy_model.setFilterFixedString(search_text)

        # 状态提示：根据复选框与关键字内容更新
        if self.show_all_checkbox.isChecked():
            # 仅显示搜索结果
            if not self.proxy_model._has_filter:
                self.status_changed.emit(Status.FILTER_EMPTY, "normal")
            else:
                self.status_changed.emit(Status.filter_by(search_text), "normal")
        else:
            # 显示全部数据（仍受类别筛选影响）
            self.status_changed.emit(Status.FILTER_ALL, "normal")

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

    # ------------------------------------------------------------------
    # 右键上下文菜单
    # ------------------------------------------------------------------
    def _show_context_menu(self, pos) -> None:
        """在密码表格上弹出行级操作菜单。"""
        index = self.table_view.indexAt(pos)
        if not index.isValid():
            return
        # 高亮当前行，确保后续操作针对这一行
        self.table_view.selectRow(index.row())

        source_index = self.proxy_model.mapToSource(index)
        source_row = source_index.row()
        if source_row < 0 or source_row >= len(self.table_model._data):
            return
        item = self.table_model._data[source_row]

        menu = QMenu(self.table_view)

        act_edit = menu.addAction("编辑…")
        act_edit.triggered.connect(self.edit_selected_password)

        menu.addSeparator()

        act_copy_user = menu.addAction("复制账号")
        user_text = str(item.get("userID") or "")
        act_copy_user.setEnabled(bool(user_text))
        act_copy_user.triggered.connect(lambda _=False, t=user_text: self._copy_plain(t, "账号"))

        act_copy_pwd = menu.addAction("复制密码")
        act_copy_pwd.setEnabled(bool(item.get("pwd")))
        pwd_proxy = self.proxy_model.index(index.row(), PasswordTableModel.password_column())
        act_copy_pwd.triggered.connect(lambda _=False, i=pwd_proxy: self.copy_cell_to_clipboard(i))

        if item.get("totp_secret"):
            act_copy_totp = menu.addAction("复制动态码")
            totp_proxy = self.proxy_model.index(index.row(), PasswordTableModel.totp_column())
            act_copy_totp.triggered.connect(lambda _=False, i=totp_proxy: self._copy_totp_at(i))

        url_text = str(item.get("url") or "").strip()
        if url_text:
            act_copy_url = menu.addAction("复制网址")
            act_copy_url.triggered.connect(lambda _=False, t=url_text: self._copy_plain(t, "网址"))
            act_open_url = menu.addAction("打开网址")
            act_open_url.triggered.connect(lambda _=False, t=url_text: self._open_url(t))

        menu.addSeparator()

        act_delete = menu.addAction("删除")
        act_delete.triggered.connect(self.delete_selected_password)

        viewport = self.table_view.viewport()
        global_pos = viewport.mapToGlobal(pos) if viewport is not None else QCursor.pos()
        menu.exec(global_pos)

    def _copy_plain(self, text: str, label: str) -> None:
        """将文本复制到剪贴板并提示。非敏感字段（账号/网址）不自动清空。"""
        if not text:
            return
        QApplication.clipboard().setText(text)  # type: ignore
        QToolTip.showText(QCursor.pos(), Tooltip.copied_plain(label), self.table_view)
        self._show_status(Status.copied_plain(label), highlight=True)

    def _open_url(self, url: str) -> None:
        """调用系统浏览器打开 URL。支持多 URL 字段（取第一个），缺失 scheme 时补 https://。"""
        tokens = [t for t in re.split(r"[\s,;]+", (url or "").strip()) if t]
        if not tokens:
            return
        first = tokens[0]
        if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.\-]*://", first):
            first = "https://" + first
        QDesktopServices.openUrl(QUrl(first))

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
        QToolTip.showText(QCursor.pos(), Tooltip.PWD_COPIED, self.table_view)

        # 2) 底部状态栏高亮提示（绿色加粗， success 级别）
        self.status_changed.emit(Status.PWD_COPIED_WITH_HINT, "success")

        # 定时清空剪贴板，避免残留敏感信息
        QTimer.singleShot(10000, lambda: QApplication.clipboard().clear())  # type: ignore
        # 2.5s 后清空状态栏（但如期间文案已被别的操作替换，则不覆盖）
        self._schedule_status_reset(Status.PWD_COPIED_WITH_HINT)

    # ------------------------------------------------------------------
    # 密码明文显示切换
    # ------------------------------------------------------------------
    def on_table_cell_clicked(self, index) -> None:
        """统一处理密码列 / “显示”列 / “动态码”列的点击行为。"""
        if not index.isValid():
            return
        col = index.column()
        if col == PasswordTableModel.reveal_column():
            self._toggle_reveal_at(index)
        elif col == PasswordTableModel.password_column():
            self.copy_cell_to_clipboard(index)
        elif col == PasswordTableModel.totp_column():
            self._copy_totp_at(index)

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
            self._show_status(Status.pwd_reveal_visible(duration), highlight=True)
        else:
            self._show_status(Status.PWD_REVEAL_HIDDEN, highlight=False)

    def _auto_hide_reveal(self, rid: int) -> None:
        """到期自动隐藏指定行的密码。"""
        self._reveal_timers.pop(rid, None)
        source_row = self.table_model.row_by_id(rid)
        if source_row < 0:
            return
        if self.table_model.is_revealed(source_row):
            self.table_model.set_revealed(source_row, False)
            self._show_status(Status.PWD_REVEAL_AUTO_HIDDEN, highlight=False)

    # 底部状态栏由 MainWindow 接收 status_changed 信号后渲染，这里只负责 emit 和自动清空。

    def _schedule_status_reset(self, text: str, delay_ms: int = 2500) -> None:
        """delay_ms 后，若状态栏文案仍为 text，则发 空串 清空。

        外层 label 不在此处持有，无法直接读取当前文案；改用 sentinel 机制：
        记录最后一次 emit 的文案 self._last_status_text，到期时核对不一致说明被
        别的调用替换了，不再清空。
        """
        self._last_status_text = text

        def _maybe_clear() -> None:
            if getattr(self, "_last_status_text", None) == text:
                self.status_changed.emit("", "normal")
                self._last_status_text = ""

        QTimer.singleShot(delay_ms, _maybe_clear)

    def _show_status(self, text: str, *, highlight: bool) -> None:
        """闪提示：emit 信号给 MainWindow，2.5 秒后自动息灭。"""
        level = "highlight" if highlight else "normal"
        self.status_changed.emit(text, level)
        self._schedule_status_reset(text)

    def save(self):
        """保存数据"""
        return self.operations.save()

    # ------------------------------------------------------------------
    # 动态码列刷新 & 复制
    # ------------------------------------------------------------------
    def _refresh_totp_column(self) -> None:
        n = self.table_model.rowCount()
        if n <= 0:
            return
        col = PasswordTableModel.totp_column()
        top = self.table_model.index(0, col)
        bottom = self.table_model.index(n - 1, col)
        self.table_model.dataChanged.emit(top, bottom, [Qt.ItemDataRole.DisplayRole])

    def _copy_totp_at(self, proxy_index) -> None:
        """复制所选行的当前动态码到剪贴板。"""
        source_index = self.proxy_model.mapToSource(proxy_index)
        source_row = source_index.row()
        if source_row < 0 or source_row >= len(self.table_model._data):
            return
        item = self.table_model._data[source_row]
        try:
            code = PasswordTableModel.compute_totp_code(item)
        except ValidationError as ex:
            QToolTip.showText(QCursor.pos(), Tooltip.totp_invalid(str(ex)), self.table_view)
            self._show_status(Status.TOTP_INVALID, highlight=True)
            return
        if not code:
            QToolTip.showText(QCursor.pos(), Tooltip.TOTP_NOT_ENABLED, self.table_view)
            return
        QApplication.clipboard().setText(code)  # type: ignore
        QToolTip.showText(QCursor.pos(), Tooltip.totp_copied(code), self.table_view)
        self._show_status(Status.totp_copied_with_hint(code), highlight=True)
        QTimer.singleShot(10000, lambda: QApplication.clipboard().clear())  # type: ignore
