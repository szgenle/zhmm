import json
import os
import platform
import subprocess
import sys
from importlib.resources import files
from pathlib import Path

from PyQt6.QtCore import QStandardPaths
from PyQt6.QtWidgets import QMessageBox


def is_macos():
    return platform.system() == "darwin"


def get_files_content(file_paths):
    content = ""
    for file_path in file_paths:
        with open(file_path, 'r', encoding="utf-8") as file:
            content += '\n' + file.read()
    return content


def get_file_content(file_path):
    with open(file_path, 'r') as file:
        return file.read()


def load_json(filepath: str, default=None):
    if not os.path.exists(filepath):
        return default
    if not os.path.isfile(filepath):
        return default
    json_data = default
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
    finally:
        return json_data


def save_json(filepath: str, json_data):
    try:
        with open(str(filepath), 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        QMessageBox.critical(None, "错误", f"保存数据失败: {str(e)}")


def rm_file(filepath):
    if os.path.exists(filepath):
        os.remove(filepath)


def resource_Path(file_name):
    if getattr(sys, 'frozen', False):
        # noinspection PyProtectedMember
        base_dir = sys._MEIPASS # type: ignore
        return Path(base_dir, "resources", file_name)
    else:
        path: str = str(files("resources").joinpath(file_name))
        return Path(path)


data_dir = None


def get_writable_dir():
    """ 获取平台合规的可写数据目录 """
    global data_dir
    if data_dir is None:
        data_dir = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.AppDataLocation
        )
        data_dir = os.path.join(data_dir, 'zhmm')
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
    return data_dir


def get_full_path(file_name):
    return Path(get_writable_dir(), file_name)


def get_application_support_path():
    # 获取Application Support目录
    paths = QStandardPaths.standardLocations(QStandardPaths.StandardLocation.AppDataLocation)
    if paths:
        return paths[0]
    return None


def open_directory(path):
    """
    打开指定目录的系统文件管理器。

    :param path: 要打开的目录路径
    """
    # 确保路径存在
    if not os.path.exists(path):
        print(f"路径 '{path}' 不存在")
        return

    # 根据操作系统调用相应的命令
    system = platform.system()
    if system == "Darwin":  # macOS
        subprocess.run(["open", path])
    elif system == "Windows":  # Windows
        subprocess.run(["explorer", path])
    elif system == "Linux":  # Linux
        subprocess.run(["xdg-open", path])
    else:
        raise OSError(f"不支持的操作系统: {system}")