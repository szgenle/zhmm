from PyQt6.QtCore import QCoreApplication

QCoreApplication.setApplicationName("zhmm")
QCoreApplication.setOrganizationName("szgenle")  # 替换为您的组织名称

from zhmm.app_setting import AppSetting

setting = AppSetting()

from zhmm.app_config import AppConfig

config = AppConfig()
