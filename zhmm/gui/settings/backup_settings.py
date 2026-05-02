#!/usr/bin/env python3
"""备份设置管理模块"""

from PyQt6.QtWidgets import (
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

import zhmm
from zhmm.config.constants import ZhmmFileInfo


class BackupSettings(QWidget):
    """备份设置组件（手动备份与备份管理）"""

    def __init__(self, info: ZhmmFileInfo, parent=None):
        super().__init__(parent)
        self.info = info
        self.setup_ui()

    def setup_ui(self):
        """设置备份界面"""
        backup_layout = QVBoxLayout(self)
        backup_layout.setContentsMargins(0, 0, 0, 0)

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
            backup_path = backup_service.create(file_path, "manual", config_file_path)
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
