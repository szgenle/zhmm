#!/usr/bin/env python3
# coding=utf-8
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QSpinBox, QCheckBox, QPushButton
from zhmm import config
from zhmm.data_exporter import DataExporter
from zhmm.ui.login_dialog import ZhmmFileInfo


class SettingWidget(QWidget):
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


        layout.addStretch()

    def export_passwords(self):
        """导出密码列表"""
        sm_data = self.info['sm_data']
        if sm_data:
            DataExporter.export_to_file(sm_data.mm['data'])

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