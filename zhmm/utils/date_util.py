#!/usr/bin/env python3
# @Date: 2024-06-30
# @LastEditTime: 2024-07-02
import time
from datetime import date, datetime


def today_str() -> str:
    return date.today().strftime("%Y-%m-%d")


def filename() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S").replace(":", "")


def time_now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def timestamp_int() -> int:
    return int(time.time())
