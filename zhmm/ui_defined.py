from typing import Optional, TypedDict

from zhmm.sm_data import SmData


class ZhmmFileInfo(TypedDict):
    file_path: str
    openid: str
    hashpw: str
    sm_data: Optional[SmData]
