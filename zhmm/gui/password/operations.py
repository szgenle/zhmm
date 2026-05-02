#!/usr/bin/env python3
"""密码数据操作逻辑"""

from zhmm.core import totp as totp_mod
from zhmm.core.errors import ValidationError
from zhmm.data.sm_data_manager import SmData
from zhmm.data.sm_data_types import ZhmmDict
from zhmm.utils.log import logger


class PasswordOperations:
    """密码数据操作管理器"""

    def __init__(self, gl_data: SmData):
        self.gl_data = gl_data

    @staticmethod
    def validate_totp_input(secret: str, algo: str, digits: int, period: int) -> tuple[bool, str]:
        """校验 TOTP 输入是否合法。

        secret 为空表示未启用，直接视为合法；非空时必须能成功 decode + generate 一次。
        """
        if not secret:
            return True, ""
        try:
            totp_mod.generate(secret, algo=algo or totp_mod.DEFAULT_ALGO, digits=digits, period=period, now=0)
            return True, ""
        except ValidationError as ex:
            return False, f"TOTP 配置无效: {ex}"

    def add_password(self, password_data: ZhmmDict) -> tuple[bool, str]:
        """
        添加密码数据

        Args:
            password_data: 密码数据字典

        Returns:
            (成功标志, 消息)
        """
        # 验证必填字段
        if not password_data.get("userID"):
            return False, "账号不能为空"

        # 可选 TOTP 校验
        ok, msg = self._check_totp(password_data)
        if not ok:
            return False, msg

        try:
            self.gl_data.add(password_data)
            if self.save():
                return True, "账号密码添加成功"
            else:
                return False, "添加失败，无法保存数据"
        except Exception as e:
            logger.error(f"添加密码出错: {str(e)}")
            return False, f"添加出错: {str(e)}"

    def delete_password(self, row: int) -> tuple[bool, str]:
        """
        删除密码数据

        Args:
            row: 要删除的行索引

        Returns:
            (成功标志, 消息)
        """
        try:
            # 从数据源中删除
            deleted_item = self.gl_data.mm["data"].pop(row)

            # 保存更改
            if not self.save():
                # 保存失败，回滚
                self.gl_data.mm["data"].insert(row, deleted_item)
                return False, "删除失败，数据保存错误"

            return True, "删除成功"
        except Exception as e:
            logger.error(f"删除账号出错: {str(e)}")
            return False, f"删除失败: {str(e)}"

    def update_password(self, row: int, new_data: ZhmmDict) -> tuple[bool, str]:
        """
        更新密码数据

        Args:
            row: 要更新的行索引
            new_data: 新的密码数据

        Returns:
            (成功标志, 消息)
        """
        # 保留原始ID和创建时间
        new_data["id"] = self.gl_data.mm["data"][row]["id"]
        if "ctime" in self.gl_data.mm["data"][row]:
            new_data["ctime"] = self.gl_data.mm["data"][row]["ctime"]  # type: ignore

        # 验证必填字段
        if not new_data.get("userID"):
            return False, "账号不能为空"

        # 可选 TOTP 校验
        ok, msg = self._check_totp(new_data)
        if not ok:
            return False, msg

        try:
            # 更新数据
            self.gl_data.mm["data"][row] = new_data
            if self.save():
                return True, "修改成功"
            else:
                return False, "修改失败，无法保存数据"
        except Exception as e:
            logger.error(f"编辑账号出错: {str(e)}")
            return False, f"修改失败: {str(e)}"

    def add_role(self, new_role: str) -> bool:
        """
        添加新角色

        Args:
            new_role: 新角色名称

        Returns:
            成功标志
        """
        if "roles" not in self.gl_data.mm or self.gl_data.mm["roles"] is None:
            self.gl_data.mm["roles"] = []

        if new_role not in self.gl_data.mm["roles"]:
            self.gl_data.mm["roles"].append(new_role)
            return self.save()

        return True

    def save(self) -> bool:
        """保存数据到本地文件。

        Returns:
            成功标志
        """
        return self.gl_data.save()

    # ------------------------------------------------------------------
    # 内部工具
    # ------------------------------------------------------------------
    @staticmethod
    def _check_totp(data: dict) -> tuple[bool, str]:
        """从 dict 中担取 TOTP 字段并校验。"""
        secret = str(data.get("totp_secret") or "").strip()
        algo = str(data.get("totp_algo") or "").strip().upper()
        try:
            digits = int(data.get("totp_digits") or totp_mod.DEFAULT_DIGITS)
            period = int(data.get("totp_period") or totp_mod.DEFAULT_PERIOD)
        except (TypeError, ValueError):
            return False, "TOTP 位数/周期必须为整数"
        return PasswordOperations.validate_totp_input(secret, algo, digits, period)
