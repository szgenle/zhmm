#!/usr/bin/env python3
# coding=utf-8
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (QButtonGroup, QGroupBox,
                             QLabel, QPushButton, QRadioButton, QSpinBox,
                             QVBoxLayout, QWidget, QMessageBox)

import zhmm
from zhmm.ui_defined import ZhmmFileInfo
from zhmm.window_setting.change_openid_dialog import ChangeOpenIdDialog
from zhmm.window_setting.import_export_handlers import ImportExportHandlers
from zhmm.window_setting.backup_settings import BackupSettings
from zhmm.window_setting.cloud_sync_handlers import CloudSyncHandlers
from zhmm.utils import file_util


class SettingWindow(QWidget):
    """设置界面组件"""

    imported_xlsx = pyqtSignal()  # 登录成功信号
    backup_settings_changed = pyqtSignal()  # 备份设置变更信号

    def __init__(self, info: ZhmmFileInfo, parent=None):
        super().__init__(parent)
        self.info = info

        # 初始化功能处理器
        self.import_export_handlers = ImportExportHandlers(self, info)
        self.cloud_sync_handlers = CloudSyncHandlers(self, info)

        self.setup_ui()

    def setup_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)

        # 自动锁定时间设置
        self.lock_time_label = QLabel("自动锁定时间（分钟）:")
        self.lock_time_spinbox = QSpinBox()
        self.lock_time_spinbox.setRange(1, 60)
        self.lock_time_spinbox.setValue(zhmm.config.get_lock_time())
        self.lock_time_spinbox.valueChanged.connect(zhmm.config.save_lock_time)
        self.lock_time_spinbox.setMaximumWidth(200)

        # 主题设置
        theme_group = QGroupBox("主题设置")
        theme_layout = QVBoxLayout()

        self.theme_button_group = QButtonGroup(self)
        self.light_theme_radio = QRadioButton("浅色主题")
        self.dark_theme_radio = QRadioButton("深色主题")
        self.auto_theme_radio = QRadioButton("跟随系统")

        self.theme_button_group.addButton(self.light_theme_radio)
        self.theme_button_group.addButton(self.dark_theme_radio)
        self.theme_button_group.addButton(self.auto_theme_radio)

        theme_layout.addWidget(self.light_theme_radio)
        theme_layout.addWidget(self.dark_theme_radio)
        theme_layout.addWidget(self.auto_theme_radio)
        theme_group.setLayout(theme_layout)
        theme_group.setMaximumWidth(300)

        # 从配置加载当前主题
        current_theme = zhmm.config.get_theme()
        if current_theme == 'dark':
            self.dark_theme_radio.setChecked(True)
        elif current_theme == 'auto':
            self.auto_theme_radio.setChecked(True)
        else:
            self.light_theme_radio.setChecked(True)

        # 连接主题切换信号
        self.theme_button_group.buttonClicked.connect(self.on_theme_changed)

        # 更改OpenID
        self.change_openid_button = QPushButton("更改OpenID")
        self.change_openid_button.clicked.connect(self.change_openid)
        self.change_openid_button.setMaximumWidth(200)

        # 导入xlsx文件
        self.import_xlsx_button = QPushButton("导入xlsx文件")
        self.import_xlsx_button.clicked.connect(self.import_xlsx)
        self.import_xlsx_button.setMaximumWidth(200)

        # 下载xlsx模版
        self.download_xlsx_button = QPushButton("下载xlsx模版")
        self.download_xlsx_button.clicked.connect(self.download_xlsx_template)
        self.download_xlsx_button.setMaximumWidth(200)

        export_button = QPushButton("导出xlsx文件")
        export_button.clicked.connect(self.export_passwords)
        export_button.setMaximumWidth(200)

        layout.addWidget(self.lock_time_label)
        layout.addWidget(self.lock_time_spinbox)

        # 自动备份设置组件
        self.backup_settings_widget = BackupSettings(self.info, self)
        self.backup_settings_widget.backup_settings_changed.connect(
            lambda: self.backup_settings_changed.emit()
        )
        backup_group = QGroupBox("自动备份设置")
        backup_group_layout = QVBoxLayout()
        backup_group_layout.addWidget(self.backup_settings_widget)
        backup_group.setLayout(backup_group_layout)
        backup_group.setMaximumWidth(400)
        layout.addWidget(backup_group)

        layout.addWidget(theme_group)
        layout.addWidget(self.change_openid_button)
        layout.addWidget(self.import_xlsx_button)
        layout.addWidget(self.download_xlsx_button)
        layout.addWidget(export_button)

        # 打开日志目录按钮
        open_log_button = QPushButton("打开日志目录")
        open_log_button.clicked.connect(self.open_log_dir)
        open_log_button.setMaximumWidth(200)
        layout.addWidget(open_log_button)

        # 云同步设置
        self.cloud_sync_handlers.setup_cloud_sync_ui(layout)

        # 版本号显示
        from zhmm import __version__
        version_label = QLabel(f"版本号: {__version__}")
        version_label.setStyleSheet("color: gray; font-size: 12px;")
        layout.addWidget(version_label)

        layout.addStretch()

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

    def open_log_dir(self):
        """打开日志目录"""
        path = file_util.get_full_path(".log").as_posix()
        file_util.open_directory(path)

    def change_openid(self):
        """更改OpenID"""
        from datetime import datetime

        current_openid = self.info.get("openid", "")
        dialog = ChangeOpenIdDialog(current_openid, self)

        if dialog.exec():
            new_openid = dialog.get_new_openid()
            if new_openid:
                # 更新内存中的OpenID
                self.info["openid"] = new_openid

                # 更新保存的文件信息
                file_path = self.info.get("file_path")
                if file_path:
                    storage_path = file_util.get_full_path(".zhmm_files.json").as_posix()
                    saved_files = file_util.load_json(storage_path) or {}

                    if file_path in saved_files:
                        saved_files[file_path]["openid"] = new_openid
                        saved_files[file_path]["last_access_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        file_util.save_json(storage_path, saved_files)

                QMessageBox.information(
                    self,
                    "更改成功",
                    f"OpenID已成功更改为：{new_openid}\n\n"
                    "注意：如需在微信小程序中使用，请确保与小程序中显示的OpenID一致。"
                )

    def on_theme_changed(self, button):
        """主题切换事件处理"""
        from PyQt6.QtWidgets import QApplication
        from zhmm.theme_manager import ThemeManager

        # 确定选择的主题
        if button == self.light_theme_radio:
            theme = 'light'
        elif button == self.dark_theme_radio:
            theme = 'dark'
        elif button == self.auto_theme_radio:
            theme = 'auto'
        else:
            return

        # 保存主题设置
        zhmm.config.save_theme(theme)

        # 应用主题
        app_instance = QApplication.instance()
        if app_instance and isinstance(app_instance, QApplication):
            stylesheet = ThemeManager.get_theme_stylesheet(theme)
            app_instance.setStyleSheet(stylesheet)
