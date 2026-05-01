#!/usr/bin/env bash
# macOS: 将 GUI 构建产物安装到 /Applications。
# 需要对 /Applications 有写入权限。
set -euo pipefail

rm -rf /Applications/zhmm.app
mv ./dist/zhmm.app /Applications/
echo "✓ Installed to /Applications/zhmm.app"
