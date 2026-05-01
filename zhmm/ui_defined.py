from typing import TypedDict

from zhmm.data.sm_data_manager import SmData


class ZhmmFileInfo(TypedDict):
    file_path: str
    openid: str
    hashpw: str
    sm_data: SmData | None
