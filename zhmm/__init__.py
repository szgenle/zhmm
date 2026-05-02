"""zhmm - 账号密码管理工具"""

from __future__ import annotations

from zhmm.config.app_config import AppConfig

# 延迟导入，避免导入时副作用
from zhmm.config.settings import AppSetting

__version__ = "0.2.2"

# 模块级变量，由 init_app 初始化
setting: AppSetting | None = None
config: AppConfig | None = None


def init_app() -> tuple[AppSetting, AppConfig]:
    """初始化应用配置和设置"""
    global setting, config

    from PyQt6.QtCore import QCoreApplication

    QCoreApplication.setApplicationName("zhmm")
    QCoreApplication.setOrganizationName("szgenle")

    setting = AppSetting()
    config = AppConfig(setting)

    return setting, config
