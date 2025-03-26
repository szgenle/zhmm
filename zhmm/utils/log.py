# -*- coding: utf-8 -*-
import logging
from datetime import datetime

import file_sys

path_file = file_sys.get_full_path(".log/%s.log" % datetime.now().strftime("%Y%m%d"))
path_file.parent.mkdir(exist_ok=True)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename=path_file,  # 日志文件名
    filemode='a'  # 追加模式
)

# 创建一个日志记录器
logger = logging.getLogger()


def log(message, level=logging.INFO):
    if not message:
        return
    msg_strip = message.strip()
    if msg_strip:  # 忽略空行
        logger.log(level, msg_strip)


def info(message):
    log(message, logging.INFO)


def error(message):
    log(message, logging.ERROR)


def debug(message):
    log(message, logging.DEBUG)


def warning(message):
    log(message, logging.WARNING)