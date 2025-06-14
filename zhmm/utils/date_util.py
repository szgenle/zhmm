#!/usr/bin/env python3
# coding=utf-8
# @Date: 2024-06-30
# @LastEditTime: 2024-07-02
import time
from datetime import date, datetime


def today_str():
    return date.today().strftime("%Y-%m-%d")


def filename():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S").replace(":", "")


def time_now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def timestamp_int():
    return int(time.time())
