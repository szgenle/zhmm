#!/usr/bin/env bash
# 将 CLI 构建产物（--onedir 目录）移动到目标位置，并在 PATH 目录中建立可执行软链。
# 用法:
#   bash mv_cmd.sh                                  # 默认安装
#   INSTALL_DIR=/opt/zhmm BIN_DIR=/usr/local/bin bash mv_cmd.sh
#
# 默认安装位置：
#   目录产物 → $HOME/.local/share/zhmm_cmd
#   可执行软链 → $HOME/.local/bin/zhmm_cmd
set -euo pipefail

INSTALL_DIR="${INSTALL_DIR:-$HOME/.local/share/zhmm_cmd}"
BIN_DIR="${BIN_DIR:-$HOME/.local/bin}"

SRC_DIR="./dist/zhmm_cmd"

if [[ ! -d "$SRC_DIR" ]]; then
    echo "✗ 未找到产物目录：$SRC_DIR"
    echo "  请先执行 make build-cmd 构建。"
    exit 1
fi

mkdir -p "$(dirname "$INSTALL_DIR")"
mkdir -p "$BIN_DIR"

# 覆盖式安装目录
rm -rf "$INSTALL_DIR"
mv -f "$SRC_DIR" "$INSTALL_DIR"

# 创建/更新可执行软链
ln -sfn "$INSTALL_DIR/zhmm_cmd" "$BIN_DIR/zhmm_cmd"

echo "✓ 目录已安装到 $INSTALL_DIR"
echo "✓ 可执行软链：$BIN_DIR/zhmm_cmd -> $INSTALL_DIR/zhmm_cmd"

# 提醒 PATH
case ":$PATH:" in
    *":$BIN_DIR:"*) ;;
    *)
        echo ""
        echo "⚠ $BIN_DIR 不在 PATH 中，请在 ~/.zshrc 或 ~/.bashrc 里添加："
        echo "    export PATH=\"$BIN_DIR:\$PATH\""
        ;;
esac
