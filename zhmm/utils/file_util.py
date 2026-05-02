"""跨平台文件与目录工具。"""

from __future__ import annotations

import json
import logging
import os
import platform
import subprocess
import sys
from importlib.resources import files
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# 应用身份（对应 Qt 的 organizationName / applicationName）
# 默认值与 GUI init_app() 一致，让 CLI 和 GUI 使用同一个数据目录：
#   macOS: ~/Library/Application Support/szgenle/zhmm
# GUI 入口会通过 set_app_identity() 重复设置（幂等、无副作用）。
_org_name: str | None = "szgenle"
_app_name: str | None = "zhmm"


def set_app_identity(org_name: str | None, app_name: str | None) -> None:
    """注入组织名 / 应用名，用于拼接 AppDataLocation。仅 GUI 初始化时调用。"""
    global _org_name, _app_name, data_dir
    _org_name = org_name or None
    _app_name = app_name or None
    # 清空缓存，让下次调用基于新的 identity 重新计算
    data_dir = None


def _default_app_data_base() -> str:
    """返回当前平台的 AppDataLocation 基础目录（不含 org/app 子目录）。"""
    system = platform.system()
    if system == "Darwin":
        return str(Path.home() / "Library" / "Application Support")
    if system == "Windows":
        appdata = os.environ.get("APPDATA")
        if appdata:
            return appdata
        return str(Path.home() / "AppData" / "Roaming")
    # Linux / 其他 Unix：遵循 XDG 规范
    xdg = os.environ.get("XDG_DATA_HOME")
    if xdg:
        return xdg
    return str(Path.home() / ".local" / "share")


def _compose_app_data_path() -> str:
    """按 Qt AppDataLocation 的规则拼接完整路径。"""
    base = _default_app_data_base()
    if _org_name and _app_name:
        return os.path.join(base, _org_name, _app_name)
    if _app_name:
        return os.path.join(base, _app_name)
    return base


def is_macos() -> bool:
    return platform.system() == "darwin"


def get_files_content(file_paths: list[str | Path]) -> str:
    content = ""
    for file_path in file_paths:
        with open(file_path, encoding="utf-8") as file:
            content += "\n" + file.read()
    return content


def get_file_content(file_path: str | Path, default: str | None = None) -> str | None:
    if not os.path.exists(file_path):
        return default
    with open(file_path) as file:
        return file.read()


def set_file_content(file_path: str | Path, content: str) -> bool:
    try:
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(content)
            return True
    except Exception as e:
        logger.error("写入文本文件失败: %s", str(e))
        return False


def set_file_bytes(file_path: str | Path, content: bytes) -> bool:
    try:
        with open(file_path, "wb") as file:
            file.write(content)
            return True
    except Exception as e:
        logger.error("写入二进制文件失败: %s", str(e))
        return False


def load_json(filepath: str, default: Any = None) -> Any:
    if not os.path.exists(filepath):
        return default
    if not os.path.isfile(filepath):
        return default
    json_data: Any = default
    try:
        with open(filepath, encoding="utf-8") as f:
            json_data = json.load(f)
    except Exception as e:
        logger.error("加载JSON失败: %s", str(e))
    return json_data


def save_json(filepath: str, json_data: Any) -> bool:
    try:
        with open(str(filepath), "w", encoding="utf-8") as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error("保存JSON失败: %s", str(e))
        return False


def rm_file(filepath: str | Path) -> None:
    if os.path.exists(filepath):
        os.remove(filepath)


def resource_Path(file_name: str) -> Path:
    if getattr(sys, "frozen", False):
        # noinspection PyProtectedMember
        base_dir = sys._MEIPASS  # type: ignore[attr-defined]
        return Path(base_dir, "resources", file_name)
    path: str = str(files("resources").joinpath(file_name))
    return Path(path)


data_dir: str | None = None


def get_writable_dir() -> str:
    """获取平台合规的可写数据目录"""
    global data_dir
    if data_dir is None:
        # 用原生实现替代 QStandardPaths，避免 CLI 场景引入 PyQt6
        data_dir = _compose_app_data_path()
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        print("数据目录:", data_dir)
    return data_dir


def get_full_path(file_name: str) -> Path:
    return Path(get_writable_dir(), file_name)


def get_application_support_path() -> str | None:
    # 返回Application Support目录（等同于 Qt AppDataLocation 的首项）
    path = _compose_app_data_path()
    return path if path else None


def open_directory(path: str | Path) -> None:
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
        subprocess.run(["open", str(path)])
    elif system == "Windows":  # Windows
        subprocess.run(["explorer", str(path)])
    elif system == "Linux":  # Linux
        subprocess.run(["xdg-open", str(path)])
    else:
        raise OSError(f"不支持的操作系统: {system}")
