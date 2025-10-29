# -*- coding: utf-8 -*-
# coding=utf-8
# @Date: 2025-03-27
# @LastEditTime: 2025-03-27
import logging
from datetime import datetime

from zhmm.utils import file_util

# 配置日志
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)  # 设置总日志级别为最低

# 模块级别的配置标志，防止重复配置
_logger_configured = False

# 防重复:若已配置过则直接返回
if _logger_configured:
    pass
else:
    # 创建不同级别的文件路径
    info_path = file_util.get_full_path(
        f".log/{datetime.now().strftime('%Y%m%d')}_info.log"
    )
    error_path = file_util.get_full_path(
        f".log/{datetime.now().strftime('%Y%m%d')}_error.log"
    )
    for path in [info_path, error_path]:
        path.parent.mkdir(exist_ok=True)

    # 定义通用日志格式
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    # 使用按日轮转的文件处理器（保留最近7天）
    import logging.handlers
    info_handler = logging.handlers.TimedRotatingFileHandler(
        info_path.as_posix(), when="midnight", backupCount=7, encoding="utf-8"
    )
    info_handler.setLevel(logging.INFO)
    info_handler.setFormatter(formatter)

    error_handler = logging.handlers.TimedRotatingFileHandler(
        error_path.as_posix(), when="midnight", backupCount=7, encoding="utf-8"
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)

    # 控制台处理器（彩色）
    class ColorFormatter(logging.Formatter):
        COLOR_CODES = {
            logging.DEBUG: "\033[94m",
            logging.INFO: "\033[92m",
            logging.WARNING: "\033[93m",
            logging.ERROR: "\033[91m",
            logging.CRITICAL: "\033[91;1m",
        }
        RESET_CODE = "\033[0m"

        def format(self, record):
            color = self.COLOR_CODES.get(record.levelno, "")
            formatter = logging.Formatter(
                f"{color}%(asctime)s - %(levelname)s - %(message)s{self.RESET_CODE}"
            )
            return formatter.format(record)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(ColorFormatter())

    # 添加所有处理器
    logger.addHandler(info_handler)
    logger.addHandler(error_handler)
    logger.addHandler(console_handler)

    # 标记已配置，避免重复添加
    _logger_configured = True


if __name__ == "__main__":
    # 使用示例
    logger.debug("调试信息")  # 仅当设置DEBUG级别时可见
    logger.info("常规信息")  # 会写入info.log和控制台
    logger.warning("警告信息")  # 会写入info.log（因为INFO处理器接受WARNING）
    logger.error("错误信息")  # 会写入error.log和控制台
    logger.critical("严重错误")  # 会写入error.log和控制台

    # 带参数的日志
    logger.info("用户登录: %s", "test_user")

    # 异常记录
    try:
        1 / 0
    except Exception as e:
        logger.exception("发生异常: ")
