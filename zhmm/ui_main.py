#!/usr/bin/env python3
# @Date: 2024-07-03
# @LastEditTime: 2024-07-03
from PyQt6.QtCore import QTimer, pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QPushButton, QTabWidget, QVBoxLayout, QWidget

import zhmm
from zhmm.core.backup_service import BackupService
from zhmm.core.errors import StorageError
from zhmm.ui_defined import ZhmmFileInfo
from zhmm.utils import file_util
from zhmm.utils.log import logger
from zhmm.window_password.password_window import PasswordWindow
from zhmm.window_setting.setting_window import SettingWindow


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
        self.setting_widget.backup_settings_changed.connect(self.start_auto_backup_timer)

        # 自动备份定时器
        self.backup_manager = BackupService(file_util.get_full_path(".backups"))
        self.backup_timer = QTimer(self)
        self.backup_timer.timeout.connect(self.auto_backup)

        self.setup_ui()
        self.start_auto_backup_timer()

    def setup_ui(self):
        # 创建主布局
        main_layout = QVBoxLayout(self)

        # 创建标签容器
        tab_widget = QTabWidget()
        main_layout.addWidget(tab_widget)

        # 添加标签页
        tab_widget.addTab(self.data_manager_widget, "账号管理")
        tab_widget.addTab(self.setting_widget, "系统设置")

        # 创建返回按钮区域（放在最下方）
        button_layout = QHBoxLayout()
        return_btn = QPushButton("返回首页")
        return_btn.clicked.connect(self.return_requested.emit)
        button_layout.addWidget(return_btn)
        button_layout.addStretch()
        main_layout.addLayout(button_layout)

    def imported_xlsx_data(self):
        if self.data_manager_widget:
            self.data_manager_widget.refresh_data()

    def start_auto_backup_timer(self):
        """启动自动备份定时器"""
        if zhmm.config.get_auto_backup_enabled():
            interval = zhmm.config.get_backup_interval()
            self.backup_timer.start(interval * 60 * 1000)  # 转换为毫秒
            logger.info(f"自动备份已启用，间隔：{interval}分钟")
        else:
            self.backup_timer.stop()
            logger.info("自动备份已禁用")

    def auto_backup(self):
        """自动备份函数"""
        file_path = self.info.get("file_path")
        if not file_path:
            logger.warning("自动备份失败：未找到数据文件")
            return

        try:
            backup_path = self.backup_manager.create(file_path, "backup")
        except StorageError as e:
            logger.error(f"自动备份失败：{e}")
            return

        # 清理旧备份
        keep_count = zhmm.config.get_backup_keep_count()
        deleted = self.backup_manager.cleanup(keep_count, "backup")

        logger.info(f"自动备份成功：{backup_path}")
        if deleted > 0:
            logger.info(f"已清理 {deleted} 个旧备份")
