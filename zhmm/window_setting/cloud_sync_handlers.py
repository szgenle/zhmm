#!/usr/bin/env python3
# coding=utf-8
"""云同步功能处理器"""
from PyQt6.QtWidgets import (
    QButtonGroup,
    QGroupBox,
    QHBoxLayout,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

import zhmm
from zhmm.ui_defined import ZhmmFileInfo
from zhmm.utils import file_util
from zhmm.window_setting.credentials_input_dialog_cos import CredentialsDialogCos


class CloudSyncHandlers:
    """处理云同步相关操作"""

    def __init__(self, parent: QWidget, info: ZhmmFileInfo):
        self.parent = parent
        self.info = info
        self.sync_group = None
        self.cos_radio = None

    def setup_cloud_sync_ui(self, main_layout: QVBoxLayout):
        """初始化云同步界面"""
        # 添加数据存储设置标签
        from PyQt6.QtWidgets import QLabel

        datasave_label = QLabel("云存储位置")
        datasave_label.setObjectName("setting-datasave-title")
        main_layout.addWidget(datasave_label)

        work_dir_container = QVBoxLayout()
        # 新增工作目录选择
        self.sync_group = QButtonGroup(self.parent)

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
                editor_button.clicked.connect(lambda: CredentialsDialogCos(self.parent).exec())

            group_layout.addWidget(radio_btn)
            group_layout.addWidget(sync_button)
            group_layout.addWidget(editor_button)

            work_dir_container.addWidget(group_box)

        # 从配置加载上次选择
        cloud_platform = zhmm.config.get("cloud_platform", "")
        if self.cos_radio:
            self.cos_radio.setChecked(cloud_platform == "cos")

        main_layout.addLayout(work_dir_container)

        # 连接信号保存配置
        self.sync_group.buttonToggled.connect(self._sync_workdir_preference)

    def _sync_workdir_preference(self, button, checked):
        """保存云存储偏好"""
        if not checked:
            return
        if button == self.cos_radio:
            platform = "cos"
        else:
            platform = ""
        zhmm.config.reset_sync_cloud(platform)

    def sync_data(self, cloud_type: str):
        """同步数据到云端或从云端拉取"""
        # 检查云配置是否有效
        if not zhmm.config.cloud:
            QMessageBox.warning(self.parent, "同步失败", "云存储未配置,请先点击'编辑'填写凭证并保存。")
            return

        # 同步方式选择
        msg = QMessageBox(self.parent)
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
                QMessageBox.information(self.parent, "同步完成", "已从云端拉取并覆盖本地文件。")
            else:
                QMessageBox.warning(self.parent, "同步失败", "云端未找到数据或读取失败。")

        elif msg.clickedButton() == push_btn:
            if zhmm.config.upload_cloud(file_path):
                QMessageBox.information(self.parent, "同步完成", "已推送本地数据到云端。")
            else:
                QMessageBox.warning(self.parent, "同步失败", "推送失败，请检查云存储配置。")
