#!/usr/bin/env python3
"""备份设置管理模块"""
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

import zhmm
from zhmm.config.constants import ZhmmFileInfo


class BackupSettings(QWidget):
    """备份设置组件"""

    backup_settings_changed = pyqtSignal()  # 备份设置变更信号

    def __init__(self, info: ZhmmFileInfo, parent=None):
        super().__init__(parent)
        self.info = info
        self.setup_ui()

    def setup_ui(self):
        """设置自动备份界面"""
        backup_layout = QVBoxLayout(self)
        backup_layout.setContentsMargins(0, 0, 0, 0)

        # 启用自动备份复选框
        self.auto_backup_checkbox = QCheckBox("启用自动备份")
        self.auto_backup_checkbox.setChecked(zhmm.config.get_auto_backup_enabled())
        self.auto_backup_checkbox.toggled.connect(self.on_auto_backup_toggled)
        backup_layout.addWidget(self.auto_backup_checkbox)

        # 备份间隔设置
        interval_layout = QHBoxLayout()
        interval_label = QLabel("备份间隔（分钟）:")
        self.backup_interval_spinbox = QSpinBox()
        self.backup_interval_spinbox.setRange(5, 1440)  # 5分钟到24小时
        self.backup_interval_spinbox.setValue(zhmm.config.get_backup_interval())
        self.backup_interval_spinbox.valueChanged.connect(zhmm.config.save_backup_interval)
        self.backup_interval_spinbox.setMaximumWidth(120)
        interval_layout.addWidget(interval_label)
        interval_layout.addWidget(self.backup_interval_spinbox)
        interval_layout.addStretch()
        backup_layout.addLayout(interval_layout)

        # 备份保留数量设置
        keep_layout = QHBoxLayout()
        keep_label = QLabel("保留备份数量:")
        self.backup_keep_spinbox = QSpinBox()
        self.backup_keep_spinbox.setRange(1, 100)
        self.backup_keep_spinbox.setValue(zhmm.config.get_backup_keep_count())
        self.backup_keep_spinbox.valueChanged.connect(zhmm.config.save_backup_keep_count)
        self.backup_keep_spinbox.setMaximumWidth(120)
        keep_layout.addWidget(keep_label)
        keep_layout.addWidget(self.backup_keep_spinbox)
        keep_layout.addStretch()
        backup_layout.addLayout(keep_layout)

        # 手动备份按钮
        manual_backup_button = QPushButton("立即备份")
        manual_backup_button.clicked.connect(self.manual_backup)
        manual_backup_button.setMaximumWidth(200)
        backup_layout.addWidget(manual_backup_button)

        # 查看备份按钮
        view_backups_button = QPushButton("管理备份")
        view_backups_button.clicked.connect(self.view_backups)
        view_backups_button.setMaximumWidth(200)
        backup_layout.addWidget(view_backups_button)

    def on_auto_backup_toggled(self, checked):
        """自动备份开关切换事件"""
        zhmm.config.save_auto_backup_enabled(checked)
        # 发出信号通知主窗口重启定时器
        self.backup_settings_changed.emit()

    def manual_backup(self):
        """手动备份"""
        from pathlib import Path

        from zhmm.core.backup_service import BackupService
        from zhmm.core.errors import StorageError
        from zhmm.utils import file_util

        file_path = self.info.get("file_path")
        if not file_path:
            QMessageBox.warning(self, "备份失败", "未找到数据文件")
            return

        # 获取配置文件路径
        data_file_name = Path(file_path).stem
        config_file_path = str(file_util.get_full_path(data_file_name))

        backup_service = BackupService(file_util.get_full_path(".backups"))
        try:
            backup_path = backup_service.create(
                file_path, "manual", config_file_path
            )
        except StorageError as e:
            QMessageBox.critical(self, "备份失败", f"备份操作失败：{e}")
            return

        # 清理旧备份
        keep_count = zhmm.config.get_backup_keep_count()
        deleted = backup_service.cleanup(keep_count, "manual")

        msg = f"备份成功！\n\n数据文件：{backup_path}"
        config_backup = backup_path.with_suffix(".config")
        if config_backup.exists():
            msg += f"\n配置文件：{config_backup}"
        if deleted > 0:
            msg += f"\n\n已清理 {deleted} 个旧备份"
        QMessageBox.information(self, "备份成功", msg)

    def view_backups(self):
        """查看和管理备份"""
        from zhmm.gui.settings.backup_list_dialog import BackupListDialog

        dialog = BackupListDialog(self.info, self)
        dialog.exec()
