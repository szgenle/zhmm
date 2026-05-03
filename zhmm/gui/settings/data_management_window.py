#!/usr/bin/env python3
"""「数据管理」标签页。

聚合所有**对存量数据做批量操作**的入口：
- 数据备份（自动备份策略 / 手动备份 / 备份列表）
- 数据导入导出（xlsx 导入 / 模板下载 / xlsx 导出）
- 标签管理（重命名 / 删除）

与「系统设置」Tab 拆分的理由：这些功能的共同特征是**直接读写密码数据**，
语义上与「应用偏好 / 账号安全」（账号信息、主题、自动锁、主密码）不同，
独立成 Tab 可降低「系统设置」页的视觉密度并提升发现性。
"""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from zhmm.config.constants import ZhmmFileInfo
from zhmm.gui.settings.backup_settings import BackupSettings
from zhmm.gui.settings.import_export_handlers import ImportExportHandlers
from zhmm.gui.settings.tag_management_dialog import TagManagementDialog
from zhmm.gui.texts import Tags as TagsText

# 与 SettingWindow 保持一致的按钮尺寸，避免同一应用中按钮风格漂移
_BUTTON_MIN_WIDTH = 140
_BUTTON_MIN_HEIGHT = 32


class DataManagementWindow(QWidget):
    """数据管理界面组件"""

    # 导入 xlsx 成功后触发，主窗口据此刷新密码表
    imported_xlsx = pyqtSignal()
    # 标签批量变更（重命名 / 删除）后发射，供主窗口刷新密码表与标签侧边栏。
    # 与 imported_xlsx 语义不同：数据结构未新增条目，仅某些条目的 tags 字段被修改。
    tags_changed = pyqtSignal()

    def __init__(self, info: ZhmmFileInfo, parent=None):
        super().__init__(parent)
        self.info = info

        # 初始化功能处理器
        self.import_export_handlers = ImportExportHandlers(self, info)

        self.setup_ui()

    def setup_ui(self):
        """初始化界面"""
        # 外层使用滚动区域，保持与「系统设置」一致的观感
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        outer_layout.addWidget(scroll)

        container = QWidget()
        scroll.setWidget(container)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # ---------- 数据备份 ----------
        layout.addWidget(self._build_backup_group())

        # ---------- 数据导入导出 ----------
        layout.addWidget(self._build_import_export_group())

        # ---------- 标签管理 ----------
        layout.addWidget(self._build_tag_management_group())

        layout.addStretch()

    # ------------------------------------------------------------------
    # 分组构建
    # ------------------------------------------------------------------
    def _build_backup_group(self) -> QGroupBox:
        """数据备份组"""
        group = QGroupBox("数据备份")
        v = QVBoxLayout()
        v.setContentsMargins(4, 8, 4, 8)
        self.backup_settings_widget = BackupSettings(self.info, self)
        v.addWidget(self.backup_settings_widget)
        group.setLayout(v)
        return group

    def _build_import_export_group(self) -> QGroupBox:
        """数据导入导出组：按钮采用网格布局，等宽整齐"""
        group = QGroupBox("数据导入导出")
        grid = QGridLayout()
        grid.setContentsMargins(4, 8, 4, 8)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)

        self.import_xlsx_button = self._make_button("导入 xlsx 文件", self.import_xlsx)
        self.download_xlsx_button = self._make_button("下载 xlsx 模版", self.download_xlsx_template)
        self.export_button = self._make_button("导出 xlsx 文件", self.export_passwords)

        grid.addWidget(self.import_xlsx_button, 0, 0)
        grid.addWidget(self.download_xlsx_button, 0, 1)
        grid.addWidget(self.export_button, 0, 2)
        grid.setColumnStretch(3, 1)  # 右侧留白

        group.setLayout(grid)
        return group

    def _build_tag_management_group(self) -> QGroupBox:
        """标签管理分组：入口按钮打开 TagManagementDialog。

        标签数据是 PasswordEntry.tags 的并集，没有独立存储，批量重命名 / 删除
        统一走 SmData.rename_tag / delete_tag 并立即落盘。
        """
        group = QGroupBox(TagsText.GROUP_TITLE)
        v = QHBoxLayout()
        v.setContentsMargins(4, 8, 4, 8)
        v.setSpacing(10)
        self.tag_manage_button = self._make_button(TagsText.BTN_OPEN, self.open_tag_management_dialog)
        v.addWidget(self.tag_manage_button)
        v.addStretch()
        group.setLayout(v)
        return group

    @staticmethod
    def _make_button(text: str, slot) -> QPushButton:
        """创建统一尺寸的按钮"""
        btn = QPushButton(text)
        btn.setMinimumWidth(_BUTTON_MIN_WIDTH)
        btn.setMinimumHeight(_BUTTON_MIN_HEIGHT)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(slot)
        return btn

    # ------------------------------------------------------------------
    # 事件处理
    # ------------------------------------------------------------------
    def export_passwords(self):
        """导出密码列表"""
        self.import_export_handlers.export_passwords()

    def import_xlsx(self):
        """导入 xlsx 文件"""

        def on_success():
            # 发送信号通知界面刷新
            self.imported_xlsx.emit()

        self.import_export_handlers.import_xlsx(on_success)

    def download_xlsx_template(self):
        """下载 xlsx 模版文件"""
        self.import_export_handlers.download_xlsx_template()

    # ------------------------------------------------------------------
    # 标签管理
    # ------------------------------------------------------------------
    def open_tag_management_dialog(self) -> None:
        """打开「标签管理」对话框；若有变更，通知主窗口刷新 UI。"""
        from PyQt6.QtWidgets import QMessageBox

        sm_data = self.info.get("sm_data")
        if not sm_data:
            QMessageBox.warning(self, TagsText.TITLE, "数据管理器未初始化")
            return
        dlg = TagManagementDialog(sm_data, parent=self)
        dlg.exec()
        if dlg.has_changes():
            self.tags_changed.emit()
