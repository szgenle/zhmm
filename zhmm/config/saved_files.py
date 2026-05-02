"""``saved_files`` 索引文件（``~/.../zhmm/.zhmm_files.json``）读写工具。

该 JSON 以 ``file_path`` 为键，保存每个密码库文件最近访问时间、账号、
bcrypt 哈希等登录元数据。原本读写逻辑分散在 :class:`FileListWidget` 里，
现在抽到独立模块以便设置页的"更换主密码"等功能直接复用。
"""

from __future__ import annotations

from typing import Any

from zhmm.utils import file_util

_STORAGE_FILE_NAME = ".zhmm_files.json"


def get_storage_path() -> str:
    """返回 saved_files 索引文件的绝对路径（POSIX 风格字符串）。"""
    return file_util.get_full_path(_STORAGE_FILE_NAME).as_posix()


def load_all() -> dict[str, dict[str, Any]]:
    """加载全部已保存文件记录；文件不存在或解析失败返回空 dict。"""
    files = file_util.load_json(get_storage_path())
    if not files or not isinstance(files, dict):
        return {}
    # 显式构造 dict 以满足 mypy 严格的类型收窄（file_util.load_json 返回 Any）
    return dict(files)


def save_all(file_infos: dict[str, dict[str, Any]]) -> bool:
    """整体覆写 saved_files 索引文件。"""
    return file_util.save_json(get_storage_path(), file_infos)


def update_entry(file_path: str, patch: dict[str, Any]) -> bool:
    """对指定 ``file_path`` 的条目做部分字段覆盖。

    不存在则忽略（返回 False）；存在则写回磁盘（返回 True）。
    """
    data = load_all()
    entry = data.get(file_path)
    if entry is None:
        return False
    entry.update(patch)
    data[file_path] = entry
    return save_all(data)
