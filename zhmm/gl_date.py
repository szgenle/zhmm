#!/usr/bin/env python3
# coding=utf-8
# @Date: 2024-06-30
# @LastEditTime: 2024-07-02
from datetime import datetime
import time


def time_now():
    now = datetime.now()
    return now.strftime('%Y-%m-%d %H:%M:%S')


def timestamp_int():
    return int(time.time())