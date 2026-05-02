"""跨模块常量与共享 TypedDict。"""

from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from zhmm.data.sm_data_manager import SmData


class ZhmmFileInfo(TypedDict):
    """已打开的密码库会话信息。"""

    file_path: str
    openid: str
    hashpw: str
    sm_data: SmData | None
