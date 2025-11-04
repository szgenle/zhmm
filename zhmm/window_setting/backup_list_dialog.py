#!/usr/bin/env python3
# coding=utf-8
"""
备份列表管理对话框
显示所有备份文件，支持恢复和删除操作
"""
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QDialog, QHBoxLayout, QLabel, QListWidget,
                             QListWidgetItem, QMessageBox, QPushButton,
                             QVBoxLayout)

from zhmm.backup_manager import BackupManager
from zhmm.ui_defined import ZhmmFileInfo


class BackupListDialog(QDialog):
    """备份列表对话框"""

    def __init__(self, info: ZhmmFileInfo, parent=None):
        super().__init__(parent)
        self.info = info
        self.backup_manager = BackupManager()
        self.setWindowTitle("备份管理")
        self.setMinimumSize(700, 500)
        self.setup_ui()
        self.load_backups()

    def setup_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)

        # 说明标签
        info_label = QLabel("自动备份和手动备份列表（双击可恢复备份，含配置文件）")
        info_label.setStyleSheet("color: #666; padding: 5px;")
        layout.addWidget(info_label)

        # 备份列表
        self.backup_list = QListWidget()
        self.backup_list.setAlternatingRowColors(True)
        self.backup_list.itemDoubleClicked.connect(self.restore_backup)
        layout.addWidget(self.backup_list)

        # 统计信息标签
        self.stats_label = QLabel()
        self.stats_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.stats_label.setStyleSheet("color: #888; padding: 5px;")
        layout.addWidget(self.stats_label)

        # 按钮区域
        button_layout = QHBoxLayout()

        self.restore_button = QPushButton("恢复选中备份")
        self.restore_button.clicked.connect(lambda: self.restore_backup(self.backup_list.currentItem()))
        self.restore_button.setEnabled(False)

        self.delete_button = QPushButton("删除选中备份")
        self.delete_button.clicked.connect(self.delete_backup)
        self.delete_button.setEnabled(False)

        self.refresh_button = QPushButton("刷新列表")
        self.refresh_button.clicked.connect(self.load_backups)

        close_button = QPushButton("关闭")
        close_button.clicked.connect(self.close)

        button_layout.addWidget(self.restore_button)
        button_layout.addWidget(self.delete_button)
        button_layout.addStretch()
        button_layout.addWidget(self.refresh_button)
        button_layout.addWidget(close_button)

        layout.addLayout(button_layout)

        # 列表选择变化事件
        self.backup_list.itemSelectionChanged.connect(self.on_selection_changed)

    def load_backups(self):
        """加载备份列表"""
        self.backup_list.clear()

        # 获取所有备份（自动备份和手动备份）
        auto_backups = self.backup_manager.get_backup_list("backup")
        manual_backups = self.backup_manager.get_backup_list("manual")
        all_backups = auto_backups + manual_backups

        # 按时间排序
        all_backups.sort(key=lambda x: x.stat().st_mtime, reverse=True)

        # 添加到列表
        for backup_path in all_backups:
            item = QListWidgetItem()
            item.setText(self.format_backup_info(backup_path))
            item.setData(Qt.ItemDataRole.UserRole, str(backup_path))
            self.backup_list.addItem(item)

        # 更新统计信息
        total_size = self.backup_manager.get_backup_size()
        self.stats_label.setText(
            f"共 {len(all_backups)} 个备份，总大小：{self.backup_manager.format_size(total_size)}"
        )

    def format_backup_info(self, backup_path: Path) -> str:
        """
        格式化备份信息显示

        Args:
            backup_path: 备份文件路径

        Returns:
            格式化后的信息字符串
        """
        try:
            # 获取文件信息
            stat = backup_path.stat()
            size = self.backup_manager.format_size(stat.st_size)
            mtime = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")

            # 判断备份类型
            backup_type = "手动备份" if backup_path.name.startswith("manual") else "自动备份"

            # 检查是否有配置文件备份
            config_backup = backup_path.parent / backup_path.name.replace(".gl", ".config")
            has_config = "[含配置]" if config_backup.exists() else ""

            return f"[{backup_type}] {backup_path.name}  {has_config}  |  {size}  |  {mtime}"

        except Exception:
            return backup_path.name

    def on_selection_changed(self):
        """列表选择变化事件"""
        has_selection = bool(self.backup_list.currentItem())
        self.restore_button.setEnabled(has_selection)
        self.delete_button.setEnabled(has_selection)

    def restore_backup(self, item: QListWidgetItem | None):
        """恢复备份"""
        if not item:
            return

        backup_path = item.data(Qt.ItemDataRole.UserRole)
        target_path = self.info.get("file_path")

        if not target_path:
            QMessageBox.warning(self, "恢复失败", "未找到目标文件路径")
            return

        # 确认恢复
        reply = QMessageBox.question(
            self,
            "确认恢复",
            f"确定要恢复此备份吗？\n\n{item.text()}\n\n"
            "当前数据文件和配置文件（如果有）将被备份后替换。此操作不可撤销！",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            if self.backup_manager.restore_backup(backup_path, target_path, restore_config=True):
                QMessageBox.information(
                    self,
                    "恢复成功",
                    "备份已成功恢复！\n\n请重新打开文件以加载恢复的数据。"
                )
                self.accept()  # 关闭对话框
            else:
                QMessageBox.critical(
                    self,
                    "恢复失败",
                    "备份恢复失败，请查看日志了解详情。"
                )

    def delete_backup(self):
        """删除选中的备份"""
        item = self.backup_list.currentItem()
        if not item:
            return

        backup_path = item.data(Qt.ItemDataRole.UserRole)

        # 确认删除
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除此备份吗？\n\n{item.text()}\n\n此操作不可恢复！",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                Path(backup_path).unlink()
                QMessageBox.information(self, "删除成功", "备份已删除")
                self.load_backups()  # 刷新列表
            except Exception as e:
                QMessageBox.critical(self, "删除失败", f"删除备份失败：\n\n{str(e)}")
