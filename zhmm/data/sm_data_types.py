#!/usr/bin/env python3
# @Date: 2024-06-30
# @LastEditTime: 2024-07-02
"""数据类型定义模块"""

from typing import TypedDict


class ZhmmDict(TypedDict):
    """单条密码数据的类型定义"""

    id: int | None
    role: str | None
    userID: str
    pwd: str
    phone: str | None
    email: str | None
    url: str
    desc: str
    utime: int | None
    tags: list[str] | None


class ZhmmDataDict(TypedDict):
    """密码数据集合的类型定义"""

    data: list[ZhmmDict]
    roles: list[str] | None
    utime: int | None


class SmDataConstants:
    """数据管理常量定义"""

    # 字段映射
    FIELD_MAPPING = {
        "id": "ID",
        "role": "类别",
        "userID": "账号",
        "pwd": "密码",
        "phone": "手机",
        "email": "邮箱",
        "url": "网站",
        "desc": "备注",
        "utime": "更新时间",
        "tags": "标签",
    }

    # 字段键列表
    KEYS = ["id", "role", "userID", "pwd", "phone", "email", "url", "desc", "utime", "tags"]

    # 表头列表
    HEADS = ["ID", "类别", "账号", "密码", "手机", "邮箱", "网站", "备注", "更新时间", "标签"]

    # 加密相关常量
    HASH_SUFFIX_LENGTH = 64  # 验证哈希长度（字符数）
    HASH_KEY_ENCRYPT_LENGTH = 32  # 加密哈希密钥长度
    HASH_KEY_SUFFIX_LENGTH = 32  # 验证哈希密钥长度

    # 搜索字段
    SEARCHABLE_FIELDS = ["url", "desc", "userID", "phone", "email"]
