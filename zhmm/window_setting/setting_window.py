#!/usr/bin/env python3
# coding=utf-8
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (QButtonGroup, QCheckBox, QGroupBox, QHBoxLayout,
                             QLabel, QPushButton, QRadioButton, QSpinBox,
                             QVBoxLayout, QWidget)

import zhmm
from zhmm.ui_data_exporter import UiDataExporter
from zhmm.ui_defined import ZhmmFileInfo
from zhmm.window_setting.credentials_input_dialog_cos import \
    CredentialsDialogCos
from zhmm.window_setting.change_openid_dialog import ChangeOpenIdDialog
from zhmm.utils import file_util


class SettingWindow(QWidget):
    """设置界面组件"""

    imported_xlsx = pyqtSignal()  # 登录成功信号
    backup_settings_changed = pyqtSignal()  # 备份设置变更信号

    def __init__(self, info: ZhmmFileInfo, parent=None):
        super().__init__(parent)
        self.info = info
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

        # 自动备份设置
        self.setup_auto_backup_ui(layout)

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

        self.init_sync_work_dir(layout)

        layout.addStretch()

    def setup_auto_backup_ui(self, main_layout: QVBoxLayout):
        """设置自动备份界面"""
        backup_group = QGroupBox("自动备份设置")
        backup_layout = QVBoxLayout()

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

        backup_group.setLayout(backup_layout)
        backup_group.setMaximumWidth(400)
        main_layout.addWidget(backup_group)

    def on_auto_backup_toggled(self, checked):
        """自动备份开关切换事件"""
        zhmm.config.save_auto_backup_enabled(checked)
        # 发出信号通知主窗口重启定时器
        self.backup_settings_changed.emit()

    def manual_backup(self):
        """手动备份"""
        from PyQt6.QtWidgets import QMessageBox
        from zhmm.backup_manager import BackupManager
        from zhmm.utils import file_util

        file_path = self.info.get("file_path")
        if not file_path:
            QMessageBox.warning(self, "备份失败", "未找到数据文件")
            return

        # 获取配置文件路径
        from pathlib import Path
        data_file_name = Path(file_path).stem
        config_file_path = str(file_util.get_full_path(data_file_name))

        backup_manager = BackupManager()
        backup_path = backup_manager.create_backup(file_path, "manual", config_file_path)

        if backup_path:
            # 清理旧备份
            keep_count = zhmm.config.get_backup_keep_count()
            deleted = backup_manager.cleanup_old_backups(keep_count, "manual")

            msg = f"备份成功！\n\n数据文件：{backup_path}"
            # 检查是否同时备份了配置文件
            config_backup = Path(backup_path).parent / Path(backup_path).name.replace(".gl", ".config")
            if config_backup.exists():
                msg += f"\n配置文件：{config_backup}"
            if deleted > 0:
                msg += f"\n\n已清理 {deleted} 个旧备份"
            QMessageBox.information(self, "备份成功", msg)
        else:
            QMessageBox.critical(self, "备份失败", "备份操作失败，请查看日志")

    def view_backups(self):
        """查看和管理备份"""
        from zhmm.window_setting.backup_list_dialog import BackupListDialog

        dialog = BackupListDialog(self.info, self)
        dialog.exec()

    def export_passwords(self):
        """导出密码列表"""
        sm_data = self.info["sm_data"]
        if sm_data:
            UiDataExporter.export_to_file(sm_data.mm["data"])

    def import_xlsx(self):
        """导入xlsx文件"""
        from PyQt6.QtWidgets import QFileDialog, QMessageBox

        from zhmm.data_exporter import DataImporter

        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择xlsx文件", "", "Excel文件 (*.xlsx)"
        )

        if not file_path:
            return

        try:
            imported_data = DataImporter.import_from_file(file_path)
            if not imported_data:
                QMessageBox.warning(
                    self,
                    "导入失败",
                    "无法读取xlsx文件，请检查文件格式是否正确。\n\n" +
                    "文件应包含以下列：\nID、类别、账号、密码、手机、邮箱、网站、备注、更新时间"
                )
                return

            sm_data = self.info["sm_data"]
            if not sm_data:
                QMessageBox.warning(self, "导入失败", "数据管理器未初始化")
                return

            # 合并导入的数据
            append_times, update_times = sm_data.merge(imported_data)  # type: ignore

            # 显示导入结果
            if append_times == 0 and update_times == 0:
                QMessageBox.information(
                    self,
                    "导入完成",
                    "导入完成，但没有新增或更新任何数据。\n\n" +
                    "可能所有数据都已存在且一致。"
                )
            else:
                QMessageBox.information(
                    self,
                    "导入成功",
                    f"成功导入数据！\n\n" +
                    f"新增: {append_times} 条\n" +
                    f"更新: {update_times} 条\n\n" +
                    f"总计处理: {append_times + update_times} 条数据"
                )
                # 发送信号通知界面刷新
                self.imported_xlsx.emit()

        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            QMessageBox.critical(
                self,
                "导入失败",
                f"导入xlsx文件时发生错误：\n\n{str(e)}\n\n" +
                f"请检查：\n" +
                f"1. 是否安装了 openpyxl 库\n" +
                f"2. 文件格式是否正确\n" +
                f"3. 文件是否被其他程序占用"
            )
            print(error_detail)

    def download_xlsx_template(self):
        """下载xlsx模版文件（动态生成）"""
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        from openpyxl import Workbook

        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "保存xlsx模版",
            "zhmm模版.xlsx",
            "Excel文件 (*.xlsx)"
        )
        if not save_path:
            return

        try:
            wb = Workbook()
            ws = wb.active
            if ws is None:
                raise ValueError("工作表不存在")
            ws.title = "密码模版"
            headers = ["ID", "类别", "账号", "密码", "手机", "邮箱", "网站", "备注", "更新时间"]
            ws.append(headers)
            wb.save(save_path)
            QMessageBox.information(self, "下载成功", f"模版文件已成功保存到：\n{save_path}")
        except Exception as e:
            QMessageBox.critical(self, "下载失败", f"保存模版文件时发生错误：\n\n{str(e)}")

    def init_sync_work_dir(self, main_layout: QVBoxLayout):
        # 添加数据存储设置标签
        datasave_label = QLabel("云存储位置")
        datasave_label.setObjectName("setting-datasave-title")
        main_layout.addWidget(datasave_label)

        work_dir_container = QVBoxLayout()
        # 新增工作目录选择
        self.sync_group = QButtonGroup(self)

        radios = ["腾讯云-对象存储", "阿里云-对象存储"]

        for radio in radios:
            # 创建分组容器（带边框）
            group_box = QGroupBox()
            group_box.setObjectName("cloud-storage-group")  # 可选：用于样式定制
            # 设置容器内边距（避免内容紧贴边框）
            group_layout = QHBoxLayout(group_box)
            group_layout.setContentsMargins(10, 8, 10, 8)
            group_layout.setSpacing(10)

            radio_btn = QRadioButton(radio)
            self.sync_group.addButton(radio_btn)

            sync_button = QPushButton("同步")
            sync_button.clicked.connect(lambda _, r=radio: self.sync_data(r))

            editor_button = QPushButton("编辑")
            # 根据不同存储类型绑定不同的编辑对话框
            if radio == "腾讯云-对象存储":
                self.cos_radio = radio_btn
                editor_button.clicked.connect(lambda: CredentialsDialogCos(self).exec())

            group_layout.addWidget(radio_btn)
            group_layout.addWidget(sync_button)
            group_layout.addWidget(editor_button)

            work_dir_container.addWidget(group_box)

        # # 从配置加载上次选择
        cloud_platform = zhmm.config.get("cloud_platform", "")
        self.cos_radio.setChecked(cloud_platform == "cos")

        main_layout.addLayout(work_dir_container)

        # 连接信号保存配置
        self.sync_group.buttonToggled.connect(self._sync_workdir_preference)
        # self.cos_radio.toggled.connect(self._toggle_cos_work_dir_visibility)

    def _sync_workdir_preference(self, button, checked):
        if not checked:
            return
        if button == self.cos_radio:
            platform = "cos"
        else:
            platform = ""
        zhmm.config.reset_sync_cloud(platform)

    def sync_data(self, cloud_type: str):
        from PyQt6.QtWidgets import QMessageBox

        # 检查云配置是否有效
        if not zhmm.config.cloud:
            QMessageBox.warning(self, "同步失败", "云存储未配置，请先点击“编辑”填写凭证并保存。")
            return

        # 同步方式选择
        msg = QMessageBox(self)
        msg.setWindowTitle("选择同步方式")
        msg.setText("请选择同步方向：")
        pull_btn = msg.addButton("从云拉取覆盖本地", QMessageBox.ButtonRole.ActionRole)
        push_btn = msg.addButton("推送本地到云端", QMessageBox.ButtonRole.ActionRole)
        cancel_btn = msg.addButton(QMessageBox.StandardButton.Cancel)
        msg.exec()

        if msg.clickedButton() == cancel_btn:
            return

        file_path = self.info["file_path"]

        if msg.clickedButton() == pull_btn:
            # 拉取前备份本地
            local_data = file_util.get_file_content(file_path)
            if local_data is not None:
                from datetime import datetime
                backup_path = f"{file_path}.bak_{datetime.now().strftime('%Y%m%d%H%M%S')}"
                file_util.set_file_content(backup_path, local_data)

            cloud = zhmm.config.cloud
            cloud_ver = cloud.get_file_content(f"zhmm/{zhmm.config.cfg_file_name}.ver")
            cloud_data = cloud.get_file_content(f"zhmm/{zhmm.config.cfg_file_name}.gl")

            if cloud_data:
                file_util.set_file_content(file_path, cloud_data)
                if cloud_ver:
                    zhmm.config.set("zhmm_ver", cloud_ver)
                    zhmm.config.save_config()
                QMessageBox.information(self, "同步完成", "已从云端拉取并覆盖本地文件。")
            else:
                QMessageBox.warning(self, "同步失败", "云端未找到数据或读取失败。")

        elif msg.clickedButton() == push_btn:
            if zhmm.config.upload_cloud(file_path):
                QMessageBox.information(self, "同步完成", "已推送本地数据到云端。")
            else:
                QMessageBox.warning(self, "同步失败", "推送失败，请检查云存储配置。")

    def open_log_dir(self):
        """打开日志目录"""
        path = file_util.get_full_path(".log").as_posix()
        file_util.open_directory(path)

    def change_openid(self):
        """更改OpenID"""
        from PyQt6.QtWidgets import QMessageBox
        from zhmm.utils import file_util

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
                        from datetime import datetime
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
