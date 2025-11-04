from typing import Optional, TypedDict

from zhmm.data.sm_data_manager import SmData


class ZhmmFileInfo(TypedDict):
    file_path: str
    openid: str
    hashpw: str
    sm_data: Optional[SmData]
