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
    # 类级别常量（只读，不可变）
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

    def __init__(self):
        # 实例属性，避免实例间共享状态
        self.pwd = ""
        self.openId = ""
        self.pwdHash = ""
        self.encryptHash = ""
        self.suffixHash = ""
        self.mm: ZhmmDataDict = {
            "data": [],
            "roles": ["个人", "工作", "其它"],
            "utime": 0,
        }
        self.file_path = ""

    def init(self, open_id: str, pwd: str):
        """
        初始化数据管理器（设置加密密钥）

        Args:
            open_id: 用户标识
            pwd: 密码

        Raises:
            ValueError: 当open_id或pwd为空时

        Note:
            该方法必须在使用encrypt/decrypt方法之前调用
        """
        if not open_id:
            raise ValueError("用户标识不能为空")
        if not pwd:
            raise ValueError("密码不能为空")

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

    def decrypt(self, encrypt_data: str) -> str | None:
        """
        解密数据

        Args:
            encrypt_data: 加密的数据字符串

        Returns:
            解密后的字符串，解密失败则返回None
        """
        # 验证并获取加密数据
        encrypt_mmdata = self.get_encrypt_mmdata(encrypt_data)
        if not encrypt_mmdata:
            return None

        try:
            # 解密数据
            decrypt_data = sm_util.decrypt_by_sm4(
                encrypt_mmdata, self.encryptHash
            )  # 解密，cbc 模式
            return decrypt_data.decode("utf-8")
        except Exception as e:
            print(f"[错误] 解密失败: {e}")
            return None

    def encrypt(self, data: str) -> str:
        """
        加密数据

        Args:
            data: 要加密的数据字符串

        Returns:
            加密后的数据字符串（包含数据+64位验证哈希）

        Raises:
            ValueError: 当数据为空或加密失败时
        """
        if not data:
            raise ValueError("加密数据不能为空")

        try:
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
        except Exception as e:
            raise ValueError(f"加密失败: {e}")

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

        if auto_save and (append_times + update_times > 0):
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
        保存加密数据到文件

        Args:
            file_path: 文件路径，如为None则使用self.file_path

        Returns:
            成功返回True，失败返回False
        """
        if file_path is None:
            file_path = self.file_path

        if not file_path:
            print("[错误] 文件路径为空，无法保存")
            return False

        try:
            data = self.encrypt(json.dumps(self.mm))
            data_size = len(data)
            with open(file_path, "w", encoding="utf-8") as file:
                write_size = file.write(data)
                return data_size == write_size
        except Exception as e:
            print(f"[错误] 保存文件失败: {file_path}, 原因: {e}")
            return False
