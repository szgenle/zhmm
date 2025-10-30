import json
from abc import ABC, abstractmethod
from pathlib import Path


class CloudBase(ABC):
    def __init__(self):
        pass

    @abstractmethod
    def sync_data(self):
        pass

    @abstractmethod
    def get_full_path(self, path: str) -> Path:
        pass

    @abstractmethod
    def get_file_content(self, path):
        pass

    @abstractmethod
    def set_file_content(self, path, content):
        pass

    @abstractmethod
    def rm_file(self, path) -> None:
        pass

    def load_json(self, path, default_value):
        content = self.get_file_content(path)
        if content is None:
            return default_value
        # 同时兼容 bytes 与 str
        text = content.decode("utf-8") if isinstance(content, (bytes, bytearray)) else content
        return json.loads(text)

    def save_json(self, path, data):
        content = json.dumps(data, ensure_ascii=False, indent=4)
        self.set_file_content(path, content)
        pass
