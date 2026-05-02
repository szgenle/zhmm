"""zhmm - 账号密码管理工具"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from zhmm.config.app_config import AppConfig
    from zhmm.config.settings import AppSetting

__version__ = "0.2.7"

# 模块级变量，由 init_app 初始化
setting: AppSetting | None = None
config: AppConfig | None = None


def init_app() -> tuple[AppSetting, AppConfig]:
    """初始化应用配置和设置（仅 GUI 入口调用，CLI 不依赖 PyQt6）"""
    global setting, config

    # 惰性导入：保证 CLI import zhmm 不会把 PyQt6 拉进来
    from PyQt6.QtCore import QCoreApplication

    from zhmm.config.app_config import AppConfig
    from zhmm.config.settings import AppSetting
    from zhmm.utils import file_util

    QCoreApplication.setApplicationName("zhmm")
    QCoreApplication.setOrganizationName("szgenle")
    # 同步注入到 file_util，使原生路径解析的结果与 QStandardPaths 一致
    file_util.set_app_identity("szgenle", "zhmm")

    setting = AppSetting()
    config = AppConfig(setting)

    return setting, config
