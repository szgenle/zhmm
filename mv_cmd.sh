#!/usr/bin/env bash
# 将 CLI 构建产物移动到目标目录。
# 用法:
#   bash mv_cmd.sh                 # 默认安装到 $HOME/.local/bin
#   TARGET=/usr/local/bin bash mv_cmd.sh
set -euo pipefail

TARGET="${TARGET:-$HOME/.local/bin}"
mkdir -p "$TARGET"
mv -f ./dist/zhmm_cmd "$TARGET/zhmm_cmd"
echo "✓ Installed to $TARGET/zhmm_cmd"
