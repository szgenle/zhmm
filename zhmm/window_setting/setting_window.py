#!/usr/bin/env python3
# coding=utf-8
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QSpinBox, QCheckBox, QPushButton
from PyQt6.QtWidgets import QButtonGroup, QCheckBox, QGroupBox, QHBoxLayout, QLabel, QRadioButton, QVBoxLayout, QWidget

from zhmm import config
from zhmm.ui_data_exporter import UiDataExporter
from zhmm.window_login.login_window import ZhmmFileInfo
from zhmm.window_setting.credentials_input_dialog_cos import CredentialsDialogCos


class SettingWindow(QWidget):
    """设置界面组件"""

    imported_xlsx = pyqtSignal()  # 登录成功信号

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
        self.lock_time_spinbox.setValue(config.get_lock_time())
        self.lock_time_spinbox.valueChanged.connect(config.save_lock_time)
        self.lock_time_spinbox.setMaximumWidth(200)
        
        # 主题设置
        self.dark_theme_checkbox = QCheckBox("启用深色主题(暂未实现)")

        # 更改OpenID
        self.change_openid_button = QPushButton("更改OpenID(暂未实现)")
        self.change_openid_button.setMaximumWidth(200)

        # 导入xlsx文件
        self.import_xlsx_button = QPushButton("导入xlsx文件(暂未实现)")
        self.import_xlsx_button.clicked.connect(self.import_xlsx)
        self.import_xlsx_button.setMaximumWidth(200)

        # 下载xlsx模版
        self.download_xlsx_button = QPushButton("下载xlsx模版(暂未实现)")
        self.download_xlsx_button.setMaximumWidth(200)

        export_button = QPushButton("导出xlsx文件")
        export_button.clicked.connect(self.export_passwords)
        export_button.setMaximumWidth(200)

        layout.addWidget(self.lock_time_label)
        layout.addWidget(self.lock_time_spinbox)
        layout.addWidget(self.dark_theme_checkbox)
        layout.addWidget(self.change_openid_button)
        layout.addWidget(self.import_xlsx_button)
        layout.addWidget(self.download_xlsx_button)
        layout.addWidget(export_button)

        self.init_sync_work_dir(layout)


        layout.addStretch()

    def export_passwords(self):
        """导出密码列表"""
        sm_data = self.info['sm_data']
        if sm_data:
            UiDataExporter.export_to_file(sm_data.mm['data'])

    def import_xlsx(self):
        """导入xlsx文件"""
        from PyQt6.QtWidgets import QFileDialog
        from zhmm.data_exporter import DataImporter
        
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "选择xlsx文件", 
            "", 
            "Excel文件 (*.xlsx)"
        )
        
        if file_path:
            try:
                imported_data = DataImporter.import_from_file(file_path)
                if not imported_data:
                    return False
                sm_data = self.info['sm_data']
                if sm_data:
                    """讲导入的数据合并到sm_data中"""
                    append_times, update_times = sm_data.merge(imported_data)   # type: ignore
                    if append_times is None:
                        return False
                    self.imported_xlsx.emit()
            except Exception as e:
                print(f"导入xlsx文件失败: {e}")
                
        return False

    def init_sync_work_dir(self, main_layout: QVBoxLayout):
        # 添加数据存储设置标签
        datasave_label = QLabel("云存储位置")
        datasave_label.setObjectName("setting-datasave-title")
        main_layout.addWidget(datasave_label)
        
        work_dir_container = QVBoxLayout()
        # 新增工作目录选择
        self.sync_group = QButtonGroup(self)

        radios = ['腾讯云-对象存储', '阿里云-对象存储']
        
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
            if radio == '腾讯云-对象存储':
                self.cos_radio = radio_btn
                editor_button.clicked.connect(lambda: CredentialsDialogCos(self).exec())
            elif radio == '阿里云-对象存储':
                self.oss_radio = radio_btn
                editor_button.clicked.connect(lambda: CredentialsDialogOss(self).exec())

            group_layout.addWidget(radio_btn)
            group_layout.addWidget(sync_button)
            group_layout.addWidget(editor_button)

            work_dir_container.addWidget(group_box)
        
        # # 从配置加载上次选择
        cloud_platform = config.get('cloud_platform', '')
        self.cos_radio.setChecked(cloud_platform == 'cos')
        self.oss_radio.setChecked(cloud_platform == 'oss')

        main_layout.addLayout(work_dir_container)

        # 连接信号保存配置
        self.sync_group.buttonToggled.connect(self._sync_workdir_preference)
        # self.cos_radio.toggled.connect(self._toggle_cos_work_dir_visibility)

    def _sync_workdir_preference(self, button, checked):
        if not checked:
            return
        if button == self.cos_radio:
            platform = 'cos'
        elif button == self.oss_radio:
            platform = 'oss'
        else:
            platform = ''
        config.reset_sync_cloud(platform)

    def sync_data(self, cloud_type: str):
        pass