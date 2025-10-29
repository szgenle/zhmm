import os
from pathlib import Path

from zhmm.cloud.cloud_base import CloudBase


class CloudOss(CloudBase):
    bucket: str | None = None
    work_dir = os.getcwd()

    def __init__(self):
        pass

    def init(self, config):
        # 最小实现：从配置读取bucket等参数，当前不做真实网络调用
        self.bucket = config.get("oss.bucket")
        # 返回True表示已初始化（即便bucket缺失也允许占位）
        return True

    def sync_data(self):
        pass

    def load_json(self, path, default_value):
        pass

    def get_full_path(self, path: str) -> Path:
        # OSS未实现，此处仅返回传入路径
        return Path(path)

    def get_file_content(self, path):
        # 未实现，返回None
        return None

    def set_file_content(self, path, content):
        # 未实现，返回None以表示失败
        return None

    def rm_file(self, path):
        # 未实现
        pass
