
from typing import TypedDict, Optional
from zhmm.sm_data import SmData

class ZhmmFileInfo(TypedDict):
    file_path: str
    openid: str
    hashpw: str
    sm_data: Optional[SmData]
