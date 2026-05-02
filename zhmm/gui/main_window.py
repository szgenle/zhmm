#!/usr/bin/env python3
# @Date: 2024-07-03
# @LastEditTime: 2024-07-03
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QTabWidget, QVBoxLayout, QWidget

from zhmm.config.constants import ZhmmFileInfo
from zhmm.gui.password.window import PasswordWindow
from zhmm.gui.settings.window import SettingWindow

# 底部状态栏样式（常驻上边分隔线 + 内边距，综合考虑深色主题下的可辨识度）
_STATUS_BASE_CSS = "padding: 2px 8px;"
_STATUS_LEVEL_CSS = {
    "normal": f"color: #666; font-size: 12px; {_STATUS_BASE_CSS}",
    "highlight": f"color: #c62828; font-size: 13px; font-weight: bold; {_STATUS_BASE_CSS}",
    "success": f"color: #2e7d32; font-size: 13px; font-weight: bold; {_STATUS_BASE_CSS}",
}


class MainWindow(QWidget):
    """主窗口"""

    return_requested = pyqtSignal()  # 返回首页的信号
    data_manager_widget: PasswordWindow | None = None

    def __init__(self, info: ZhmmFileInfo):
        super().__init__()
        self.info = info
        self.data_manager_widget = PasswordWindow(info)
        self.setting_widget = SettingWindow(info)
        self.setting_widget.imported_xlsx.connect(self.imported_xlsx_data)

        self.setup_ui()

    def setup_ui(self):
        # 创建主布局
        main_layout = QVBoxLayout(self)

        # 创建标签容器
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)

        # 添加标签页
        self.tab_widget.addTab(self.data_manager_widget, "账号管理")
        self.tab_widget.addTab(self.setting_widget, "系统设置")
        # 切换 tab 时清空状态栏（当前只有账号管理 tab 会向状态栏发消息）
        self.tab_widget.currentChanged.connect(lambda _i: self._set_status("", "normal"))

        # 底部行：[返回首页]  [stretch]  [状态栏]
        # 与“返回首页”同行能节省垂直空间，并且状态栏居窗口最底，符合桌面应用惯例。
        button_layout = QHBoxLayout()
        return_btn = QPushButton("返回首页")
        return_btn.clicked.connect(self.return_requested.emit)
        button_layout.addWidget(return_btn)
        button_layout.addStretch()

        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.status_label.setStyleSheet(_STATUS_LEVEL_CSS["normal"])
        # 允许状态栏左侧被按钮挤压，若文字过长可以省略号
        self.status_label.setMinimumWidth(0)
        button_layout.addWidget(self.status_label, 1)

        main_layout.addLayout(button_layout)

        # PasswordWindow 向上报告状态变更
        if self.data_manager_widget is not None:
            self.data_manager_widget.status_changed.connect(self._set_status)

    def _set_status(self, text: str, level: str) -> None:
        """更新底部状态栏文案与样式，未知 level 回落 normal。"""
        self.status_label.setText(text)
        self.status_label.setStyleSheet(_STATUS_LEVEL_CSS.get(level, _STATUS_LEVEL_CSS["normal"]))

    def imported_xlsx_data(self):
        if self.data_manager_widget:
            self.data_manager_widget.refresh_data()
