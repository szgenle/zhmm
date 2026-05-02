#!/usr/bin/env python3
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

import zhmm
from zhmm.config.constants import ZhmmFileInfo
from zhmm.gui.settings.backup_settings import BackupSettings
from zhmm.gui.settings.import_export_handlers import ImportExportHandlers

# 统一的按钮尺寸，避免大小不一造成视觉混乱
_BUTTON_MIN_WIDTH = 140
_BUTTON_MIN_HEIGHT = 32


class SettingWindow(QWidget):
    """设置界面组件"""

    imported_xlsx = pyqtSignal()  # 登录成功信号

    def __init__(self, info: ZhmmFileInfo, parent=None):
        super().__init__(parent)
        self.info = info

        # 初始化功能处理器
        self.import_export_handlers = ImportExportHandlers(self, info)

        self.setup_ui()

    def setup_ui(self):
        """初始化界面"""
        # 外层使用滚动区域，避免窗口较小时内容被压缩
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

        # ---------- 常规设置 ----------
        layout.addWidget(self._build_general_group())

        # ---------- 数据备份 ----------
        layout.addWidget(self._build_backup_group())

        # ---------- 数据导入导出 ----------
        layout.addWidget(self._build_import_export_group())

        layout.addStretch()

    # ------------------------------------------------------------------
    # 分组构建
    # ------------------------------------------------------------------
    def _build_general_group(self) -> QGroupBox:
        """常规设置：自动锁定时间 + 主题"""
        group = QGroupBox("常规")
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        form.setFormAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)

        # 自动锁定时间
        self.lock_time_spinbox = QSpinBox()
        self.lock_time_spinbox.setRange(1, 60)
        self.lock_time_spinbox.setValue(zhmm.config.get_lock_time())
        self.lock_time_spinbox.setSuffix(" 分钟")
        self.lock_time_spinbox.setFixedWidth(120)
        self.lock_time_spinbox.valueChanged.connect(zhmm.config.save_lock_time)
        form.addRow("自动锁定时间：", self.lock_time_spinbox)

        # 主题
        self.theme_button_group = QButtonGroup(self)
        self.light_theme_radio = QRadioButton("浅色")
        self.dark_theme_radio = QRadioButton("深色")
        self.auto_theme_radio = QRadioButton("跟随系统")
        for btn in (self.light_theme_radio, self.dark_theme_radio, self.auto_theme_radio):
            self.theme_button_group.addButton(btn)

        theme_row = QHBoxLayout()
        theme_row.setSpacing(16)
        theme_row.addWidget(self.light_theme_radio)
        theme_row.addWidget(self.dark_theme_radio)
        theme_row.addWidget(self.auto_theme_radio)
        theme_row.addStretch()
        theme_row_widget = QWidget()
        theme_row_widget.setLayout(theme_row)
        form.addRow("主题：", theme_row_widget)

        # 加载当前主题
        current_theme = zhmm.config.get_theme()
        if current_theme == "dark":
            self.dark_theme_radio.setChecked(True)
        elif current_theme == "auto":
            self.auto_theme_radio.setChecked(True)
        else:
            self.light_theme_radio.setChecked(True)
        self.theme_button_group.buttonClicked.connect(self.on_theme_changed)

        # 防截屏开关
        self.anti_screenshot_checkbox = QCheckBox("开启防截屏（阻止录屏/截图工具抓取窗口内容）")
        self.anti_screenshot_checkbox.setChecked(zhmm.config.get_anti_screenshot())
        self.anti_screenshot_checkbox.toggled.connect(self.on_anti_screenshot_toggled)
        form.addRow("防截屏：", self.anti_screenshot_checkbox)

        group.setLayout(form)
        return group

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
        """导入xlsx文件"""

        def on_success():
            # 发送信号通知界面刷新
            self.imported_xlsx.emit()

        self.import_export_handlers.import_xlsx(on_success)

    def download_xlsx_template(self):
        """下载xlsx模版文件"""
        self.import_export_handlers.download_xlsx_template()

    def on_theme_changed(self, button):
        """主题切换事件处理"""
        from PyQt6.QtWidgets import QApplication

        from zhmm.gui.theme import ThemeManager

        # 确定选择的主题
        if button == self.light_theme_radio:
            theme = "light"
        elif button == self.dark_theme_radio:
            theme = "dark"
        elif button == self.auto_theme_radio:
            theme = "auto"
        else:
            return

        # 保存主题设置
        zhmm.config.save_theme(theme)

        # 应用主题
        app_instance = QApplication.instance()
        if app_instance and isinstance(app_instance, QApplication):
            stylesheet = ThemeManager.get_theme_stylesheet(theme)
            app_instance.setStyleSheet(stylesheet)

    def on_anti_screenshot_toggled(self, checked: bool) -> None:
        """防截屏开关切换：持久化 + 实时对顶层窗口生效。"""
        from zhmm.utils.anti_capture import apply_anti_capture

        zhmm.config.save_anti_screenshot(checked)
        top = self.window()
        if top is not None:
            apply_anti_capture(top, enabled=checked)
