from pathlib import Path

from zhmm.cloud.cloud_base import CloudBase
from zhmm.cloud.cloud_cos import CloudCos
from zhmm.cloud.cloud_oss import CloudOss


class CloudSync:
    cloud: CloudBase = None
    platform: str = None
    work_dir: str = None

    def __init__(self, platform, config, work_dir):
        self.platform = platform
        self.work_dir = work_dir

        if platform == "cos":
            self.cloud = CloudCos(config, work_dir)
        elif platform == "oss":
            self.cloud = CloudOss(config, work_dir)
        else:
            self.cloud = None
        pass

    def sync_data(self):
        if self.cloud is None:
            return None
        return self.cloud.sync_data()

    def load_json(self, path, default_value):
        pass

    # 判断path是否是绝对路径，如果不是则拼接work_dir，否则直接返回path
    def get_full_path(self, path: str) -> Path:
        if self.cloud is None:
            return Path(path)
        return self.cloud.get_full_path(path)

    def get_file_content(self, path):
        if self.cloud is None:
            return None
        return self.cloud.get_file_content(path)

    def set_file_content(self, path, content):
        if self.cloud is None:
            return None
        return self.cloud.set_file_content(path, content)

    def rm_file(self, path):
        if self.cloud is None:
            return False
        return self.cloud.rm_file(path)
