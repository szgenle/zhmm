#!/usr/bin/env python3
# coding=utf-8
# @Date: 2024-06-30
# @LastEditTime: 2024-07-02
import json
from typing import Optional, TypedDict

from zhmm import sm_util
from zhmm.utils import data_conversion, date_util, dict_util


class ZhmmDict(TypedDict):
    id: Optional[int]
    role: Optional[str]
    userID: str
    pwd: str
    phone: Optional[str]
    email: Optional[str]
    url: str
    desc: str
    utime: Optional[int]


class ZhmmDataDict(TypedDict):
    data: list[ZhmmDict]
    roles: Optional[list[str]]
    utime: Optional[int]


class SmData:
    field_mapping = {
        "id": "ID",
        "role": "类别",
        "userID": "账号",
        "pwd": "密码",
        "phone": "手机",
        "email": "邮箱",
        "url": "网站",
        "desc": "备注",
        "utime": "更新时间",
    }

    keys = ["id", "role", "userID", "pwd", "phone", "email", "url", "desc", "utime"]
    heads = ["ID", "类别", "账号", "密码", "手机", "邮箱", "网站", "备注", "更新时间"]

    pwd = ""
    openId = ""

    pwdHash = ""
    encryptHash = ""
    suffixHash = ""

    mm: ZhmmDataDict = {
        "data": [],
        "roles": ["个人", "工作", "其它"],
        "utime": 0,
    }

    file_path = ""

    def __init__(self):
        return

    def init(self, open_id: str, pwd: str):
        """
        初始化数据管理器

        Args:
            open_id: 用户标识
            pwd: 密码
        """
        self.openId = open_id
        self.pwd = pwd

        # 计算密码哈希
        self.pwdHash = sm_util.hash_by_sm3(
            data_conversion.chars_to_bytes(self.pwd), self.openId
        )
        self.encryptHash = self.pwdHash[0:32]  # 前32位用于加密
        self.suffixHash = self.pwdHash[32:64]  # 后32位用于验证

    def get_encrypt_mmdata(self, mm_data: str) -> str | None:
        """
        获取并验证加密的数据

        Args:
            mm_data: 加密的数据字符串

        Returns:
            验证通过后的数据字符串，验证失败则返回None
        """
        if not mm_data:
            return None

        mm_data_len = len(mm_data)
        if mm_data_len <= 64:
            return None

        # 分离数据和验证哈希
        end_index = mm_data_len - 64
        suffix = mm_data[end_index:mm_data_len]  # 后64位是验证哈希
        data_part = mm_data[0:end_index]  # 前面部分是实际数据

        # 验证数据完整性
        hash_en_data = sm_util.hash_by_sm3(
            data_conversion.chars_to_bytes(data_part), self.suffixHash
        )
        if hash_en_data == suffix:
            return data_part

        return None

    def decrypt(self, encrypt_data: str) -> dict | None:
        """
        解密数据

        Args:
            encrypt_data: 加密的数据字符串

        Returns:
            解密后的数据字典，解密失败则返回None
        """
        # 验证并获取加密数据
        encrypt_mmdata = self.get_encrypt_mmdata(encrypt_data)
        if not encrypt_mmdata:
            return None

        # 解密数据
        decrypt_data = sm_util.decrypt_by_sm4(
            encrypt_mmdata, self.encryptHash
        )  # 解密，cbc 模式
        return {"res": decrypt_data.decode()}

    def encrypt(self, data: str) -> str:
        """
        加密数据

        Args:
            data: 要加密的数据字符串

        Returns:
            加密后的数据字符串
        """
        # 加密数据
        encrypt_data = sm_util.encrypt_by_sm4(data.encode("utf-8"), self.encryptHash)

        # 将加密后的字节数据转换为十六进制字符串
        hex_data = data_conversion.to_hex_string(encrypt_data)

        # 计算验证哈希
        suffix = sm_util.hash_by_sm3(
            data_conversion.chars_to_bytes(hex_data), self.suffixHash
        )

        # 返回加密数据和验证哈希的组合
        return hex_data + suffix

    def set_mm(self, user_mm_data: ZhmmDataDict):
        self.mm = user_mm_data
        if "roles" not in user_mm_data or not user_mm_data["roles"]:
            user_mm_data["roles"] = ["个人", "工作", "其它"]
        # 遍历user_mm_data['data'], 判断role是否在roles中，如果不在就添加
        for data in user_mm_data["data"]:
            if "role" not in data or not data["role"]:
                data["role"] = "个人"
            if data["role"] not in user_mm_data["roles"]:
                user_mm_data["roles"].append(data["role"])
        user_mm_data.setdefault("utime", date_util.timestamp_int())

    def fix_id_is_None(self) -> bool:
        """
        处理历史遗留的字段值问题
        查找所有数据，把id不是数字的设置为时间戳（秒），
        如果utime不是数字的也设置为时间戳（秒）。
        每秒改动一项，防止重复。
        """
        if not self.mm or not self.mm["data"]:
            return True
        finished = True
        for data in self.mm["data"]:
            if "id" not in data or not isinstance(data["id"], int):
                data["id"] = date_util.timestamp_int()
                finished = False
            if "utime" not in data or not isinstance(data["utime"], int):
                data["utime"] = date_util.timestamp_int()
                finished = False
            if not finished:
                break
        return finished

    def search(self, words: str) -> list[ZhmmDict] | None:
        if not self.mm or not self.mm["data"]:
            return None

        find_data: list[ZhmmDict] = []
        arr_words = words.split()
        for word in arr_words:
            for data in self.mm["data"]:
                if "url" in data and word in data["url"]:
                    find_data.append(data)
                elif "desc" in data and word in data["desc"]:
                    find_data.append(data)
                elif "userID" in data and word in data["userID"]:
                    find_data.append(data)
                elif "phone" in data and data["phone"] and word in data["phone"]:
                    find_data.append(data)
                elif "email" in data and data["email"] and word in data["email"]:
                    find_data.append(data)
        return find_data

    def delete(self, id: int) -> bool:
        if not self.mm or not self.mm["data"]:
            return False
        for data in self.mm["data"]:
            if "id" in data and data["id"] == id:
                self.mm["data"].remove(data)
                self.mm["utime"] = date_util.timestamp_int()
                return True
        return False

    def add(self, info: ZhmmDict):
        if "role" not in info or not info["role"]:
            info["role"] = "个人"
        if "id" not in info or not info["id"]:
            info["id"] = date_util.timestamp_int()
        if "utime" not in info or not info["utime"]:
            info["utime"] = date_util.timestamp_int()
        self.mm["data"].append(info)
        self.mm["utime"] = date_util.timestamp_int()

    def merge(self, other: list[ZhmmDict]):
        """
        将other的每一项数据合并到mm['data']中
        如果这一项中有一项不存在相同id的项中，就合并
        如果这一项中在mm['data']相同id的项中是完全一样的，就不合并
        """
        if not other:
            return

        append_times = 0
        update_times = 0
        for item in other:
            if "id" not in item:
                continue

            existing_item = next(
                (x for x in self.mm["data"] if "id" in x and x["id"] == item["id"]),
                None,
            )

            if not existing_item:
                self.mm["data"].append(item)
                self.mm["utime"] = date_util.timestamp_int()
                append_times += 1
            elif not dict_util.is_equal(existing_item, item):  # type: ignore
                """ "比较utime, 使用utime相对比较大的数据"""
                if (
                    "utime" not in item
                    or not item["utime"]
                    or "utime" not in existing_item
                    or not existing_item["utime"]
                ):
                    self.mm["data"].append(item)
                    self.mm["utime"] = date_util.timestamp_int()
                    append_times += 1
                elif item["utime"] > existing_item["utime"]:
                    print("existing_item", existing_item)
                    print("other_item", item)
                    existing_item.update(item)
                    self.mm["utime"] = date_util.timestamp_int()
                    update_times += 1
        print(f"合并完成, 新增{append_times}条, 更新{update_times}条")
        if append_times + update_times > 0:
            self.save()
        return append_times, update_times

    def add_with_dict(self, info: dict):
        self.add(
            {
                "id": info.get("id", date_util.timestamp_int()),
                "role": info.get("role", "个人"),
                "userID": info.get("userID", ""),
                "pwd": info.get("pwd", ""),
                "phone": info.get("phone", ""),
                "email": info.get("email", ""),
                "url": info.get("url", ""),
                "desc": info.get("desc", ""),
                "utime": info.get("utime", date_util.timestamp_int()),
            }
        )

    def save(self, file_path: str | None = None) -> bool:
        if file_path is None:
            file_path = self.file_path
        data = self.encrypt(json.dumps(self.mm))
        data_size = len(data)
        with open(file_path, "w") as file:
            write_size = file.write(data)
            return data_size == write_size
