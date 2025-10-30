"""zhmm - 账号密码管理工具"""

__version__ = "0.1.0"

# 延迟导入，避免导入时副作用
from zhmm.app_setting import AppSetting
from zhmm.app_config import AppConfig

# 模块级变量，由 init_app 初始化
setting = None
config = None


def init_app():
    """初始化应用配置和设置"""
    global setting, config

    from PyQt6.QtCore import QCoreApplication
    QCoreApplication.setApplicationName("zhmm")
    QCoreApplication.setOrganizationName("szgenle")

    setting = AppSetting()
    config = AppConfig(setting)

    return setting, config
