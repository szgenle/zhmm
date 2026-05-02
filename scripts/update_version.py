#!/usr/bin/env python3
"""
版本号自动更新脚本

使用规则：
- 版本号格式：主版本号.次版本号.构建号
- 每次构建时自动增加构建号
- 同时更新 pyproject.toml 和 zhmm/__init__.py 中的版本号
"""

import re
import sys
from pathlib import Path


def get_project_root() -> Path:
    """获取项目根目录"""
    return Path(__file__).parent.parent


def read_file(path: Path) -> str:
    """读取文件内容"""
    return path.read_text(encoding="utf-8")


def write_file(path: Path, content: str) -> None:
    """写入文件内容"""
    path.write_text(content, encoding="utf-8")


def increment_version(version: str) -> str:
    """
    递增版本号的构建号

    Args:
        version: 当前版本号，如 "0.1.0"

    Returns:
        新版本号，如 "0.1.1"
    """
    parts = version.split(".")
    if len(parts) >= 3:
        # 增加最后一个数字（构建号）
        parts[-1] = str(int(parts[-1]) + 1)
    elif len(parts) == 2:
        # 如果只有两位，添加构建号 1
        parts.append("1")
    else:
        # 如果只有一位，添加 .0.1
        parts.extend(["0", "1"])
    return ".".join(parts)


def update_pyproject_version(project_root: Path, new_version: str) -> str:
    """
    更新 pyproject.toml 中的版本号

    Args:
        project_root: 项目根目录
        new_version: 新版本号

    Returns:
        旧版本号
    """
    pyproject_path = project_root / "pyproject.toml"
    content = read_file(pyproject_path)

    # 查找当前版本号
    match = re.search(r'^version\s*=\s*"([^"]+)"', content, re.MULTILINE)
    if not match:
        print("错误：无法在 pyproject.toml 中找到版本号")
        sys.exit(1)

    old_version = match.group(1)

    # 替换版本号
    new_content = re.sub(r'^(version\s*=\s*")([^"]+)(")', rf"\g<1>{new_version}\g<3>", content, flags=re.MULTILINE)

    write_file(pyproject_path, new_content)
    print(f"已更新 pyproject.toml: {old_version} -> {new_version}")
    return old_version


def update_init_version(project_root: Path, new_version: str) -> str:
    """
    更新 zhmm/__init__.py 中的版本号

    Args:
        project_root: 项目根目录
        new_version: 新版本号

    Returns:
        旧版本号
    """
    init_path = project_root / "zhmm" / "__init__.py"
    content = read_file(init_path)

    # 查找当前版本号
    match = re.search(r'^__version__\s*=\s*"([^"]+)"', content, re.MULTILINE)
    if not match:
        print("错误：无法在 zhmm/__init__.py 中找到版本号")
        sys.exit(1)

    old_version = match.group(1)

    # 替换版本号
    new_content = re.sub(r'^(__version__\s*=\s*")([^"]+)(")', rf"\g<1>{new_version}\g<3>", content, flags=re.MULTILINE)

    write_file(init_path, new_content)
    print(f"已更新 zhmm/__init__.py: {old_version} -> {new_version}")
    return old_version


def get_current_version(project_root: Path) -> str:
    """获取当前版本号（从 pyproject.toml 读取）"""
    pyproject_path = project_root / "pyproject.toml"
    content = read_file(pyproject_path)

    match = re.search(r'^version\s*=\s*"([^"]+)"', content, re.MULTILINE)
    if not match:
        print("错误：无法在 pyproject.toml 中找到版本号")
        sys.exit(1)

    return match.group(1)


def main():
    """主函数"""
    project_root = get_project_root()

    # 获取当前版本号
    current_version = get_current_version(project_root)

    # 递增版本号
    new_version = increment_version(current_version)

    print(f"当前版本: {current_version}")
    print(f"新版本: {new_version}")

    # 更新两个文件
    update_pyproject_version(project_root, new_version)
    update_init_version(project_root, new_version)

    print(f"\n版本号更新完成: {current_version} -> {new_version}")
    return new_version


if __name__ == "__main__":
    main()
