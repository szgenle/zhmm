#!/usr/bin/env bash
# 将 CLI 构建产物（--onedir 目录）移动到目标位置，并在 PATH 目录中建立可执行软链。
# 安装完成后会把整个安装目录锁成只读（防止静默篡改），升级时会自动解锁再覆盖。
#
# 用法:
#   bash mv_cmd.sh                                  # 默认安装
#   INSTALL_DIR=/opt/zhmm BIN_DIR=/usr/local/bin bash mv_cmd.sh
#   NO_LOCK=1 bash mv_cmd.sh                        # 不上锁（调试用）
#
# 默认安装位置：
#   目录产物 → $HOME/.local/share/zhmm_cmd
#   可执行软链 → $HOME/.local/bin/zhmm_cmd
set -euo pipefail

INSTALL_DIR="${INSTALL_DIR:-$HOME/.local/share/zhmm_cmd}"
BIN_DIR="${BIN_DIR:-$HOME/.local/bin}"
NO_LOCK="${NO_LOCK:-0}"

SRC_DIR="./dist/zhmm_cmd"

if [[ ! -d "$SRC_DIR" ]]; then
    echo "✗ 未找到产物目录：$SRC_DIR"
    echo "  请先执行 make build-cmd 构建。"
    exit 1
fi

mkdir -p "$(dirname "$INSTALL_DIR")"
mkdir -p "$BIN_DIR"

# 覆盖式安装目录：旧目录若被锁成只读，先解锁再删除
if [[ -d "$INSTALL_DIR" ]]; then
    chmod -R u+w "$INSTALL_DIR" 2>/dev/null || true
    rm -rf "$INSTALL_DIR"
fi
mv -f "$SRC_DIR" "$INSTALL_DIR"

# 创建/更新可执行软链
ln -sfn "$INSTALL_DIR/zhmm_cmd" "$BIN_DIR/zhmm_cmd"

echo "✓ 目录已安装到 $INSTALL_DIR"
echo "✓ 可执行软链：$BIN_DIR/zhmm_cmd -> $INSTALL_DIR/zhmm_cmd"

# 权限加固：整目录设为只读，仅保留可执行文件的 x 权限
if [[ "$NO_LOCK" != "1" ]]; then
    # 1) 先给所有者加写权限，确保 chmod 能遍历
    chmod -R u+rwX "$INSTALL_DIR"
    # 2) 撤销所有用户的写权限（owner/group/other 都不可写）
    chmod -R a-w "$INSTALL_DIR"
    # 3) 确保主可执行文件仍可执行（chmod a-w 不会动 x 位，这里显式保险）
    [[ -f "$INSTALL_DIR/zhmm_cmd" ]] && chmod a+rx "$INSTALL_DIR/zhmm_cmd"
    echo "🔒 已锁定为只读（升级时脚本会自动解锁覆盖；如需手动解锁：chmod -R u+w $INSTALL_DIR）"
else
    echo "⚠ 已跳过只读锁定（NO_LOCK=1）"
fi

# 提醒 PATH
case ":$PATH:" in
    *":$BIN_DIR:"*) ;;
    *)
        echo ""
        echo "⚠ $BIN_DIR 不在 PATH 中，请在 ~/.zshrc 或 ~/.bashrc 里添加："
        echo "    export PATH=\"$BIN_DIR:\$PATH\""
        ;;
esac
