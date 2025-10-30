import os
from pathlib import Path

from zhmm.cloud.cloud_base import CloudBase
from zhmm.utils import file_util

class CloudOss(CloudBase):
    bucket: str | None = None

    def __init__(self):
        # 使用本地目录作为占位实现：AppData/.oss/{bucket}
        self.base_dir: Path | None = None

    def init(self, config):
        # 从配置读取bucket参数
        self.bucket = config.get("oss.bucket")
        # 即便bucket缺失也允许占位，但推荐提示
        if self.bucket:
            self.base_dir = file_util.get_full_path(f".oss/{self.bucket}")
            self.base_dir.mkdir(parents=True, exist_ok=True)
        return True

    def sync_data(self):
        # 占位：未实现真实同步
        return None

    def get_full_path(self, path: str) -> Path:
        if not self.base_dir:
            # 未配置bucket时仍返回原始路径
            return Path(path)
        full = self.base_dir / path
        full.parent.mkdir(parents=True, exist_ok=True)
        return full

    def get_file_content(self, path):
        # 本地文件占位实现
        full = self.get_full_path(path)
        if not full.exists():
            return None
        try:
            return full.read_text(encoding="utf-8")
        except Exception:
            return None

    def set_file_content(self, path, content):
        full = self.get_full_path(path)
        try:
            if isinstance(content, (bytes, bytearray)):
                full.write_bytes(content)
            else:
                full.write_text(str(content), encoding="utf-8")
            # 返回一个占位的ETag
            return
        except Exception:
            return

    def rm_file(self, path):
        full = self.get_full_path(path)
        try:
            if full.exists():
                full.unlink()
        except Exception:
            pass
