# -*- coding: utf-8 -*-
# coding=utf-8
# @Date: 2025-03-27
# @LastEditTime: 2025-03-27
import logging
from datetime import datetime

from zhmm.utils import file_sys

path_file = file_sys.get_full_path(".log/%s.log" % datetime.now().strftime("%Y%m%d"))
path_file.parent.mkdir(exist_ok=True)

# 配置日志
# 移除原来的basicConfig，改为手动配置logger
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)  # 设置总日志级别为最低

# 创建不同级别的文件路径
info_path = file_sys.get_full_path(f".log/{datetime.now().strftime('%Y%m%d')}_info.log")
error_path = file_sys.get_full_path(f".log/{datetime.now().strftime('%Y%m%d')}_error.log")
for path in [info_path, error_path]:
    path.parent.mkdir(exist_ok=True)

# 定义通用日志格式
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

# 创建不同处理器
info_handler = logging.FileHandler(info_path, mode='a')
info_handler.setLevel(logging.INFO)  # 只处理INFO及更高级别
info_handler.setFormatter(formatter)

error_handler = logging.FileHandler(error_path, mode='a')
error_handler.setLevel(logging.ERROR)  # 只处理ERROR及更高级别
error_handler.setFormatter(formatter)


# 控制台处理器（保留原有功能）
# 定义带颜色的控制台格式
class ColorFormatter(logging.Formatter):
    COLOR_CODES = {
        logging.DEBUG: '\033[94m',    # 蓝色
        logging.INFO: '\033[92m',     # 绿色
        logging.WARNING: '\033[93m',   # 黄色
        logging.ERROR: '\033[91m',     # 红色
        logging.CRITICAL: '\033[91;1m' # 加粗红色
    }
    RESET_CODE = '\033[0m'

    def format(self, record):
        color = self.COLOR_CODES.get(record.levelno, '')
        formatter = logging.Formatter(
            f'{color}%(asctime)s - %(levelname)s - %(message)s{self.RESET_CODE}'
        )
        return formatter.format(record)


# 修改原来的控制台处理器配置（仅修改这部分）
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(ColorFormatter())  # 使用彩色格式器

# 添加所有处理器
logger.addHandler(info_handler)
logger.addHandler(error_handler)
logger.addHandler(console_handler)


if __name__ == '__main__':
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