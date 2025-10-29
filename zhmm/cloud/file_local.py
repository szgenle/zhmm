import json
import os
from pathlib import Path

from zhmm.utils.log import logger


class FileLocal:
    work_dir = os.getcwd()

    def __init__(self, work_dir):
        if work_dir:
            self.work_dir = work_dir
        pass

    # 判断path是否是绝对路径，如果不是则拼接work_dir，否则直接返回path
    def get_full_path(self, path: str) -> Path:
        if not os.path.isabs(path):
            return Path(self.work_dir, path)
        return Path(path)

    def get_project_path(self, path):
        return Path(os.getcwd(), path)

    def get_file_content(self, path):
        full_path = self.get_full_path(path)
        if full_path.exists():
            with open(full_path, "r", encoding="utf-8") as f:
                return f.read()
        return None

    def set_file_content(self, path, content) -> bool:
        full_path = self.get_full_path(path)
        try:
            full_path.parent.mkdir(parents=True, exist_ok=True)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"文件已成功写入: {full_path}")
            return True  # 写入成功返回True
        except Exception as e:
            logger.error("文件写入失败: %s", str(e))
            return False  # 写入失败返回False

    def load_json(self, path, default_value=None):
        full_path = self.get_full_path(path)
        if full_path.exists():
            with open(full_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return default_value

    def save_json(self, path, data):
        full_path = self.get_full_path(path)
        full_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(full_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error("保存JSON失败: %s", str(e))

    def rm_file(self, path):
        full_path = self.get_full_path(path)
        if full_path.exists():
            os.remove(full_path)
