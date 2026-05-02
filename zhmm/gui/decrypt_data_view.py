"""UI 层文件解密适配器。

对外提供 `decrypt_file(path, openid, password)`：
- 文件不存在或为空：当作新建库，返回含一条示例记录的 SmData。
- 文件非空：调用 SmData.load 解密并填充数据。

`openid` 仅用于签名兼容与示例记录的用户名，不再参与密钥派生（新加密格式
使用随机盐 + PBKDF2 派生密钥）。
"""

from __future__ import annotations

from pathlib import Path

from zhmm.data.sm_data_manager import SmData
from zhmm.utils.log import logger


class UIDecryptData:
    """UI 侧解密工具类。"""

    def decrypt_file(self, file_path: str, openid: str, password: str) -> SmData | None:
        """读取并解密文件；文件为空或不存在时返回新建库。"""
        try:
            smdata = SmData()
            smdata.init(openid, password)

            p = Path(file_path)
            if not p.exists() or p.stat().st_size == 0:
                smdata.file_path = file_path
                smdata.add_with_dict(
                    {
                        "userID": openid,
                        "pwd": password,
                        "url": "szgenle",
                        "desc": "务必记住当前的账号和密码",
                    }
                )
                return smdata

            if not smdata.load(file_path):
                return None
            return smdata
        except Exception as e:
            logger.error(f"解密失败: {e!s}")
            return None
