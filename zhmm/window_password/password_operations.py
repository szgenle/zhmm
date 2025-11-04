#!/usr/bin/env python3
# coding=utf-8
"""密码数据操作逻辑"""

from PyQt6.QtWidgets import QMessageBox

from zhmm.data.sm_data_manager import SmData
from zhmm.data.sm_data_types import ZhmmDict
from zhmm.utils import date_util
from zhmm.utils.log import logger


class PasswordOperations:
    """密码数据操作管理器"""

    def __init__(self, gl_data: SmData):
        self.gl_data = gl_data

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
        """
        保存数据（包括云端上传）

        Returns:
            成功标志
        """
        import zhmm

        ret: bool = self.gl_data.save()
        # 存储云数据是可选的
        zhmm.config.upload_cloud(self.gl_data.file_path)
        return ret
