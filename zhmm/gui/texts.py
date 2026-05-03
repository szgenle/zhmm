"""GUI 文案常量骨架。

集中收敛散落在各窗口里的面向用户的短文案（状态栏、气泡、提示等），
便于日后维护、i18n（国际化）预留接口，以及避免同一文案多处硬编码
改漏（典型：复制成功提示在 emit 和 schedule_reset 两处出现）。

## 分组约定

- `Status`：底部状态栏（MainWindow.status_label）文案
- `Tooltip`：鼠标气泡（QToolTip.showText）文案
- `Filter`：搜索/筛选区相关文案

## 使用方式

```python
from zhmm.gui.texts import Status, Tooltip

# 静态文案
self.status_changed.emit(Status.PWD_REVEAL_HIDDEN, "normal")

# 需要动态参数的：走 @staticmethod 工厂
self._show_status(Status.pwd_reveal_visible(duration), highlight=True)
```

## 扩充原则

- 只收敛**面向最终用户**的文案；程序日志 / 异常 message 不纳入
- 带参数的文案用 `@staticmethod` 而非 f-string 模板，防止调用方忘传参
- 文案本身仍用中文硬编码，i18n 真正要做时再切 gettext / Qt tr()
"""

from __future__ import annotations


class Status:
    """底部状态栏文案。"""

    # ---- 筛选状态 ----
    FILTER_EMPTY = "请输入关键字以显示结果"
    FILTER_ALL = "显示全部数据"

    # ---- 密码复制 ----
    PWD_COPIED_WITH_HINT = "✅ 已复制密码到剪贴板（10 秒后自动清空）"

    # ---- 密码明文切换 ----
    PWD_REVEAL_HIDDEN = "🔒 密码已隐藏"
    PWD_REVEAL_AUTO_HIDDEN = "🔒 密码已自动隐藏"

    # ---- TOTP ----
    TOTP_INVALID = "⚠ TOTP 配置无效"

    # ---- 账户信息 ----
    ACCOUNT_COPIED_WITH_HINT = "✅ 已复制登录账号（10 秒后自动清空剪贴板）"

    @staticmethod
    def filter_by(keyword: str) -> str:
        """搜索命中时的状态文案。"""
        return f"已按“{keyword}”筛选"

    @staticmethod
    def pwd_reveal_visible(seconds: int) -> str:
        """密码被显示时带自动隐藏倒计时的文案。"""
        return f"👁 密码已显示，{seconds} 秒后自动隐藏"

    @staticmethod
    def totp_copied_with_hint(code: str) -> str:
        """复制动态码成功（带剪贴板自动清空提示）。"""
        return f"✅ 已复制动态码 {code}（10 秒后自动清空剪贴板）"

    @staticmethod
    def copied_plain(label: str) -> str:
        """复制非敏感字段（账号/网址等）。"""
        return f"✅ 已复制{label}"


class Tooltip:
    """鼠标位置气泡文案。"""

    PWD_COPIED = "✅ 已复制密码到剪贴板"
    TOTP_NOT_ENABLED = "该条目未启用 TOTP"
    ACCOUNT_COPIED = "✅ 已复制登录账号"

    @staticmethod
    def copied_plain(label: str) -> str:
        return f"✅ 已复制{label}"

    @staticmethod
    def totp_copied(code: str) -> str:
        return f"✅ 已复制动态码 {code}"

    @staticmethod
    def totp_invalid(detail: str) -> str:
        return f"⚠ TOTP 配置无效: {detail}"


class Rekey:
    """主密码更换（Re-key）相关文案。

    统一收敛对话框标题、标签、校验提示、进度阶段、
    成功 / 失败提示等，依旧例采用「静态字段 + 带参 @staticmethod」。
    """

    # ---- 对话框 ----
    TITLE = "更换主密码"
    HINT = "换密后，数据库将用新密码重新加密。账号保持不变。\n" "操作前会自动在备份目录中保存一份 rekey 备份作为保险。"
    LABEL_OLD = "当前密码："
    LABEL_NEW = "新密码："
    LABEL_CONFIRM = "确认新密码："
    BTN_OK = "确定更换"
    BTN_CANCEL = "取消"

    # ---- 校验提示 ----
    ERR_OLD_EMPTY = "请输入当前密码"
    ERR_NEW_EMPTY = "新密码不能为空"
    ERR_CONFIRM_MISMATCH = "两次输入的新密码不一致"
    ERR_SAME_AS_OLD = "新密码不能与当前密码相同"
    ERR_OLD_WRONG = "当前密码错误"

    # ---- 进度阶段 ----
    PROGRESS_TITLE = "正在更换主密码"
    STAGE_BACKUP = "正在创建保险备份…"
    STAGE_REKEY = "正在重新加密数据…"
    STAGE_FINALIZE = "正在同步会话与本地配置…"

    # ---- 结果提示 ----
    SUCCESS_TITLE = "主密码已更新"
    FAIL_TITLE = "更换失败"
    FAIL_BACKUP = "创建保险备份失败，已中止换密："
    FAIL_REKEY = "重新加密失败："
    FAIL_CONFIG_SYNC = "密库已更新，但本地配置文件同步失败。\n" "下次启动时部分偏好设置可能被重置，不影响密码数据。"

    @staticmethod
    def success_message(backup_path: str) -> str:
        """换密成功后的结果提示，附上保险备份路径。"""
        return f"主密码已更新。\n\n保险备份位于：\n{backup_path}"


class Account:
    """设置页「账户信息」分组相关文案。

    登录账号作为 KDF 输入参与密钥派生，本身不写入加密文件，若用户
    遗忘将无法解密已有数据。该分组的文案就是围绕「持续可见地回显账号 +
    牢记提示」组织的。
    """

    # ---- 分组与字段 ----
    GROUP_TITLE = "账户信息"
    LABEL_ACCOUNT = "登录账号："
    BTN_COPY = "复制账号"

    # ---- 说明文字 ----
    # 不内置换行，交给 QLabel.setWordWrap 根据容器宽度自适应
    HINT = "⚠ 该账号与登录密码共同参与数据加密，未写入加密文件。\n" "如遗忘或输错，将无法解密已有数据，请务必牢记。"


class Tags:
    """标签管理相关文案。

    设置页新增的「标签管理」分组以及其模态对话框的文案收敛在此，
    跟随 RekeyText、AccountText 使用「静态字段 + 带参 @staticmethod」风格。
    """

    # ---- 分组与按钮 ----
    GROUP_TITLE = "标签管理"
    BTN_OPEN = "管理标签"

    # ---- 对话框 ----
    TITLE = "标签管理"
    HINT = "重命名或删除任一标签，会立即同步到所有关联条目并落盘。"
    EMPTY = "当前库暂无任何标签。\n可在「账号管理」编辑条目时添加标签。"
    BTN_RENAME = "重命名…"
    BTN_DELETE = "删除"
    BTN_CLOSE = "关闭"

    # ---- 重命名输入 ----
    INPUT_TITLE = "重命名标签"
    INPUT_LABEL = "请输入新的标签名："

    # ---- 校验 / 失败提示 ----
    ERR_EMPTY = "标签名不能为空。"
    ERR_SAME = "新标签名与原名相同。"
    ERR_SAVE_FAILED = "保存失败，已还原数据。请稍后再试或检查文件权限。"

    @staticmethod
    def confirm_delete(tag: str, count: int) -> str:
        """删除确认文案。"""
        return f"确定删除标签 “#{tag}” 吗？\n将从 {count} 条记录中移除，此操作不可撤销。"

    @staticmethod
    def confirm_merge(old: str, new: str) -> str:
        """重命名到已有标签时的合并确认文案。"""
        return f"标签 “#{new}” 已存在。\n\n继续将合并：#{old} → #{new}，原 “#{old}” 将消失。\n\n是否继续？"

    @staticmethod
    def success_renamed(old: str, new: str, count: int) -> str:
        return f"已将 {count} 条记录中的 “#{old}” 重命名为 “#{new}”。"

    @staticmethod
    def success_deleted(tag: str, count: int) -> str:
        return f"已从 {count} 条记录中删除标签 “#{tag}”。"
