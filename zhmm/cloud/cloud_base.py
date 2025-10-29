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
    def rm_file(self, path):
        pass

    def load_json(self, path, default_value):
        content = self.get_file_content(path)
        if content is None:
            return default_value
        try:
            if isinstance(content, bytes):
                content_str = content.decode("utf-8")
            else:
                content_str = str(content)
            return json.loads(content_str)
        except Exception:
            return default_value

    def save_json(self, path, data):
        content = json.dumps(data, ensure_ascii=False, indent=4)
        self.set_file_content(path, content)
        pass
