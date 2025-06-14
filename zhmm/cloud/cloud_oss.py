import os
from pathlib import Path

from zhmm.cloud.cloud_base import CloudBase


class CloudOss(CloudBase):
    bucket: str = None
    work_dir = os.getcwd()

    def __init__(self, config):
        pass

    def sync_data(self):
        pass

    def load_json(self, path, default_value):
        pass

    def get_full_path(self, path: str) -> Path:
        pass

    def get_file_content(self, path):
        pass

    def set_file_content(self, path, content):
        pass

    def rm_file(self, path):
        pass
