#!/usr/bin/env python3
# coding=utf-8
# @Date: 2024-06-30
# @LastEditTime: 2024-07-02
"""数据管理模块"""

import json

from zhmm.data.sm_crypto import SmCrypto
from zhmm.data.sm_data_types import SmDataConstants, ZhmmDataDict, ZhmmDict
from zhmm.utils import date_util, dict_util


class SmData(SmCrypto):
    """数据管理器（继承加密功能）"""

    # 类级别常量（只读，不可变）
    field_mapping = SmDataConstants.FIELD_MAPPING
    keys = SmDataConstants.KEYS
    heads = SmDataConstants.HEADS

    # 加密相关常量
    HASH_SUFFIX_LENGTH = SmDataConstants.HASH_SUFFIX_LENGTH
    HASH_KEY_ENCRYPT_LENGTH = SmDataConstants.HASH_KEY_ENCRYPT_LENGTH
    HASH_KEY_SUFFIX_LENGTH = SmDataConstants.HASH_KEY_SUFFIX_LENGTH

    # 搜索字段
    SEARCHABLE_FIELDS = SmDataConstants.SEARCHABLE_FIELDS

    def __init__(self):
        super().__init__()
        # 实例属性，避免实例间共享状态
        self.mm: ZhmmDataDict = {
            "data": [],
            "roles": ["个人", "工作", "其它"],
            "utime": 0,
        }
        self.file_path = ""

    def set_mm(self, user_mm_data: ZhmmDataDict):
        """设置密码数据"""
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
        查找所有数据，把id不是数字的设置为时间戳+偏移量，
        如果utime不是数字的也设置为时间戳。
        使用偏移量保证id唯一性。

        Returns:
            True 表示所有项均已修复，False 表示还有项需要修复
        """
        if not self.mm or not self.mm["data"]:
            return True

        base_timestamp = date_util.timestamp_int()
        offset = 0
        all_fixed = True

        for data in self.mm["data"]:
            if "id" not in data or not isinstance(data["id"], int):
                data["id"] = base_timestamp + offset
                offset += 1
                all_fixed = False
            if "utime" not in data or not isinstance(data["utime"], int):
                data["utime"] = base_timestamp
                all_fixed = False

        return all_fixed

    def search(self, words: str) -> list[ZhmmDict] | None:
        """
        搜索包含关键词的数据项

        Args:
            words: 关键词，用空格分隔

        Returns:
            匹配的数据列表，无结果返回None
        """
        if not self.mm or not self.mm["data"]:
            return None

        find_data_dict: dict[int, ZhmmDict] = {}  # 用字典去重，基于id
        arr_words = words.split()

        for word in arr_words:
            word_lower = word.lower()  # 忽略大小写
            for data in self.mm["data"]:
                if "id" not in data or not data["id"]:
                    continue

                # 如果已经在结果中，跳过
                if data["id"] in find_data_dict:
                    continue

                # 在各字段中搜索（忽略大小写）
                if (
                    ("url" in data and data["url"] and word_lower in data["url"].lower())
                    or ("desc" in data and data["desc"] and word_lower in data["desc"].lower())
                    or ("userID" in data and data["userID"] and word_lower in data["userID"].lower())
                    or ("phone" in data and data["phone"] and word_lower in data["phone"].lower())
                    or ("email" in data and data["email"] and word_lower in data["email"].lower())
                ):
                    find_data_dict[data["id"]] = data

        return list(find_data_dict.values()) if find_data_dict else None

    def delete(self, id: int) -> bool:
        """
        删除指定id的数据项

        Args:
            id: 要删除的数据项id

        Returns:
            成功返回True，失败返回False
        """
        if not self.mm or not self.mm["data"]:
            return False

        # 使用列表推导式安全删除
        original_len = len(self.mm["data"])
        self.mm["data"] = [
            data for data in self.mm["data"]
            if not ("id" in data and data["id"] == id)
        ]

        # 检查是否真的删除了
        if len(self.mm["data"]) < original_len:
            self.mm["utime"] = date_util.timestamp_int()
            return True
        return False

    def add(self, info: ZhmmDict):
        """添加数据项"""
        if "role" not in info or not info["role"]:
            info["role"] = "个人"
        if "id" not in info or not info["id"]:
            info["id"] = date_util.timestamp_int()
        if "utime" not in info or not info["utime"]:
            info["utime"] = date_util.timestamp_int()
        self.mm["data"].append(info)
        self.mm["utime"] = date_util.timestamp_int()

    def merge(self, other: list[ZhmmDict], auto_save: bool = True) -> tuple[int, int]:
        """
        将other的每一项数据合并到mm['data']中
        如果这一项中有一项不存在相同id的项中，就合并
        如果这一项中在mm['data']相同id的项中是完全一样的，就不合并

        Args:
            other: 要合并的数据列表
            auto_save: 是否自动保存，默认True（保持向后兼容）

        Returns:
            (append_times, update_times) 新增数量和更新数量
        """
        if not other:
            return 0, 0

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
                # 新增项
                self.mm["data"].append(item)
                append_times += 1
            elif not dict_util.is_equal(existing_item, item):  # type: ignore
                # 比较 utime，使用 utime 相对比较大的数据
                item_utime = item.get("utime", 0) or 0
                existing_utime = existing_item.get("utime", 0) or 0

                if item_utime > existing_utime:
                    # 更新现有项
                    existing_item.update(item)
                    update_times += 1
                elif item_utime == 0 or existing_utime == 0:
                    # 如果时间戳不存在，添加为新项（保持向后兼容）
                    self.mm["data"].append(item)
                    append_times += 1

        # 更新总时间戳
        if append_times + update_times > 0:
            self.mm["utime"] = date_util.timestamp_int()
            print(f"合并完成, 新增{append_times}条, 更新{update_times}条")

            if auto_save:
                self.save()

        return append_times, update_times

    def add_with_dict(self, info: dict):
        """
        从字典添加新的密码数据项（便利方法）

        Args:
            info: 包含密码信息的字典，支持的字段：
                - id: 数据id，可选
                - role: 类别，可选，默认"个人"
                - userID: 账号，必须
                - pwd: 密码，必须
                - phone: 手机，可选
                - email: 邮箱，可选
                - url: 网站，可选
                - desc: 备注，可选
                - utime: 更新时间，可选

        Note:
            该方法会自动补全缺失的字段
        """
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

    def load(self, file_path: str | None = None) -> bool:
        """
        从文件加载并解密数据

        Args:
            file_path: 文件路径，如为None则使用self.file_path

        Returns:
            成功返回True，失败返回False
        """
        if file_path is None:
            file_path = self.file_path

        if not file_path:
            print("[错误] 文件路径为空，无法加载")
            return False

        try:
            with open(file_path, "r", encoding="utf-8") as file:
                encrypted_data = file.read()

            if not encrypted_data:
                print(f"[错误] 文件为空: {file_path}")
                return False

            # 解密数据
            decrypted_str = self.decrypt(encrypted_data)
            if not decrypted_str:
                print(f"[错误] 解密失败: {file_path}")
                return False

            # 解析JSON
            user_mm_data = json.loads(decrypted_str)  # type: ignore
            self.set_mm(user_mm_data)
            self.file_path = file_path
            return True

        except FileNotFoundError:
            print(f"[错误] 文件不存在: {file_path}")
            return False
        except json.JSONDecodeError as e:
            print(f"[错误] JSON解析失败: {file_path}, 原因: {e}")
            return False
        except Exception as e:
            print(f"[错误] 加载文件失败: {file_path}, 原因: {e}")
            return False

    def save(self, file_path: str | None = None) -> bool:
        """
        保存加密数据到文件（原子性操作）

        Args:
            file_path: 文件路径，如为None则使用self.file_path

        Returns:
            成功返回True，失败返回False

        Note:
            使用临时文件+原子性重命名确保数据安全，避免写入失败导致数据丢失
        """
        import os
        import tempfile

        if file_path is None:
            file_path = self.file_path

        if not file_path:
            print("[错误] 文件路径为空，无法保存")
            return False

        tmp_path = None
        try:
            # 加密数据
            encrypted_data = self.encrypt(json.dumps(self.mm))

            # 获取目标文件的目录和文件名
            file_dir = os.path.dirname(file_path) or "."
            file_name = os.path.basename(file_path)

            # 写入临时文件
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=file_dir,
                prefix=f".{file_name}.",
                suffix=".tmp",
                delete=False,
            ) as tmp_file:
                tmp_path = tmp_file.name
                write_size = tmp_file.write(encrypted_data)

            # 验证写入完整性
            if write_size != len(encrypted_data):
                os.unlink(tmp_path)
                print(f"[错误] 写入数据不完整: {file_path}")
                return False

            # 原子性重命名（替换目标文件）
            os.replace(tmp_path, file_path)
            return True

        except Exception as e:
            print(f"[错误] 保存文件失败: {file_path}, 原因: {e}")
            # 清理可能残留的临时文件
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except:
                    pass
            return False
