# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **密码历史版本（同条目内）**：`PasswordEntry` 新增 `history: list[PasswordHistoryItem]`，每次更新密码时自动将旧密码和时间戳压入栈顶，FIFO 上限 5 条（`core.models.HISTORY_MAX`）。
  - **写入策略**：仅当 `pwd` 实际变化且旧密码非空时压栈；修改备注 / 标签等非 `pwd` 字段不会污染历史；尽量由 `PasswordService.update` / `PasswordOperations.update_password` 统一拦截注写，调用方显式传 `history` 也会被覆盖，避免绕过记录。
  - **回滚能力**：`PasswordService.rollback(entry_id, index)` / `PasswordOperations.rollback_password(row, index)` 以「交换 + 压栈」语义将某条历史恢复为当前密码，当前密码同时压回栈顶以保留审计性（两次回滚能还原原始状态）。
  - **GUI**：密码表格右键菜单新增「查看历史密码…」（无历史时自动灰显）；历史对话框（`zhmm/gui/password/history_dialog.py`）支持按条明文切换 / 复制（10s 后自动清空剪贴板）/ 以指定历史密码恢复为当前密码（「恢复」按钮带二次确认）。回滚操作有意不做成右键快捷菜单项，统一收在对话框内部，避免误操作。
  - **存储与导出边界**：history 仅随 `.zmb` 随 SM4 加密落盘，**Excel 导出 / 导入通道刻意不承载**（避免明文历史密码扩散，导入后该条目 history 为空）；旧 `.zmb` 无该字段时反序列化得空列表，零迁移成本。
  - 新增 11 个单元测试覆盖：压栈 / 截断 / 同值不压栈 / 非 pwd 变更不污染 / 显式传入无法绕过 / 回滚交换 / 两次回滚还原 / 越界 / 旧数据缺字段 / 历史内脏数据容错 / `to_dict` 序列化。
- **条目标签（Tags）**：`PasswordEntry` 新增 `tags: list[str]` 字段，用于给密码条目贴「工作 / 家人 / 重要」等弱分类，与 `role` 互相独立（一个条目可贴 0~16 个标签，单标签 ≤ 32 字符；全局归一化走 `core.models.normalize_tags()`：`strip` / 去空 / 去重保序 / 超长截断 / 超数安静丢弃）。
  - **GUI**：添加 / 编辑对话框新增「标签」行，提供 Chip 可视化编辑器（`zhmm/widgets/tag_editor.py`）：回车 / 空格 / 分号提交、空输入框时 Backspace 删除最后一个 chip、QCompleter 联想当前库已有标签。
  - **侧边栏**：密码窗口左侧新增「标签」侧边栏（`zhmm/gui/password/tag_sidebar.py`），多选 **AND 语义** 筛选（选中「工作 + 重要」只显同时含这两个标签的条目）；标签按条目出现频次倒序展示，右侧表格通过 `QSplitter` 可拖拽调整宽度；侧边栏填充按钮一键清除筛选。
  - **表格**：「网站」与「备注」之间新增「标签」列（索引 9），以 `#a  #b` 格式展示；关键字搜索覆盖标签文本。
  - **Excel 导入导出**：表头追加「标签 / tags」列，多标签单元格用 `;` 分隔（例：`工作;重要`）；**旧 Excel 文件无此列仍可导入**（核心必填列仍为前 9 列），旧 `.zmb` 文件无 `tags` 字段默认为空列表。
  - **搜索与服务层**：`core.password_service.search()` 与 `SmData.search()` 都将标签拼为空格分隔的 haystack 纳入大小写不敏感匹配；`SmData.set_mm()` 在读入时统一调用 `normalize_tags()` 兑底，旧数据即使混有非法值也不会报错。
- **主密码更换（Re-key）**：设置页新增「更换主密码」入口，支持在不导出/重导入的前提下原地替换主密码。
  - 核心层：`core/vault.py` 新增 `VaultFile.rekey(path, account, old_password, new_password)`，流程为「用旧口令 `open` 校验 → 用新口令 `seal` 重新派生 Argon2id 密钥并加密 → 同目录临时文件 `fsync` + `os.replace` 原子替换」；任一步失败均不触碰原文件。
  - `data/sm_data_manager.py` 新增 `SmData.rekey()`，封装换密并同步更新内部 `_password`，保证后续 `save()` 使用新密钥。
  - GUI 层新增 `gui/settings/rekey_dialog.py`：模态对话框校验当前密码（bcrypt）/ 新密码非空一致性 / 新旧不相同，后台 `RekeyWorker (QThread)` 先用 `BackupService` 以 `prefix="rekey"` 生成保险备份再执行换密；成功后同步刷新当前会话 `hashpw`、`saved_files` 索引与本地配置中的 bcrypt 哈希。
  - 新增 5 个单元测试覆盖：新密码可解 / 旧密码被拒 / 错误旧密码时原文件未被破坏 / 无临时文件残留 / 目标文件缺失抛 `StorageError`。
- **账户信息设置分组**：设置页顶部新增「账户信息」分组，明文展示当前登录账号（作为 KDF 常量盐参与密钥派生，遗忘后无法解密）并提供复制按钮；复制后 10 秒自动清空剪贴板，与密码 / TOTP 的剪贴板策略保持一致。
- **登录失败限速与锁定（UI 层退避）**：登录对话框连续失败 ≥ 3 次后进入指数退避锁定（2s → 4s → 8s …，单次上限 60s）；锁定期间禁用登录按钮与密码输入框，按钮文字实时显示剩余秒数，倒计时结束后自动恢复并聚焦密码框；登录成功时计数清零。仅用于手动 GUI 重试节流，**不防御离线暴力**（攻击者可绕过 GUI 直接调用 `core.vault`，离线破解成本仍由 Argon2id 承担）。
- **密码强度可视化**：新增 `zhmm.core.password_strength` 纯函数模块 `assess_strength()`，输出 0-100 分与 5 档等级（极弱 / 弱 / 一般 / 强 / 极强），内置常见弱密码库、顺序 / 倒序序列检测、重复字符惩罚等启发式规则；新增 `PasswordStrengthBar` 控件（`zhmm/widgets/strength_bar.py`），已接入登录 / 新增密码 / 随机密码生成 / 更换主密码四处对话框，输入实时刷新颜色与提示文本。**纯离线算法，不发起任何网络请求**，与项目本地优先约束一致。
- **「数据管理」标签页**：主窗口新增顶层 Tab（`zhmm/gui/settings/data_management_window.py`），集中放置数据备份 / 导入导出 / 标签管理三个模块；设置页 `SettingWindow` 相应移除这些块，减少系统设置页视觉负担；导入完成与标签变更信号改由 `DataManagementWindow` 统一发射并传给 `MainWindow` 刷新密码表格与侧边栏。
- **标签批量重命名与删除**：「数据管理 → 标签管理」新增对话框（`zhmm/gui/settings/tag_management_dialog.py`），按使用次数倒序列出全部标签，支持重命名（与已有标签合并时自动去重 / 保序）与删除（带影响条目数二次确认）；失败时回滚内存数据避免状态不一致。`SmData` 新增 `count_tag_usages / rename_tag / delete_tag` 三个批量接口。
- `zhmm/config/saved_files.py`：集中管理 `~/.zhmm/.zhmm_files.json` 索引文件的读写（`load_all / save_all / update_entry`），原先散落在 `FileListWidget` 中的逻辑被抽出，便于更换主密码等功能复用。
- `zhmm/gui/texts.py` 新增 `Account` / `Rekey` 文案类，集中管理账户信息分组与主密码更换流程中的中文提示、阶段标签与结果消息。

### Fixed
- 备份列表对话框：在时间字段前补充「数据」前缀（形如 `数据 yyyy-MM-dd HH:mm:ss`），避免与后续文件名 / 大小列混在一起难以阅读。
- 侧边栏标签筛选与「仅显示搜索结果」复选框的交互：选择标签时自动取消「仅显示搜索结果」勾选，避免无关键字时清空标签筛选结果；复选框状态通过信号同步到代理模型并触发刷新。

### Changed
- **标签列表整行点击切换勾选**：新增 `RowToggleListWidget` 组件，标签侧边栏（`zhmm/gui/password/tag_sidebar.py`）与标签多选弹窗（`zhmm/widgets/tag_editor.py`）全部替换为该组件，点击整行即可切换勾选；禁用项不响应点击；列表样式下沉到 `zhmm/gui/theme.py` 的主题定义，统一亮色 / 深色主题下的视觉风格，去除硬编码颜色。
- **搜索输入防抖**：密码表格搜索框从 `textChanged` 即时触发改为 150 ms `QTimer` 防抖触发，减少快速输入时的无效过滤与 UI 抖动；`filter_passwords` 调用会主动取消未完成的防抖定时器避免冲突。
- `make build-app` / `build-cmd` / `build-all` 不再隐式依赖 `update-version`，避免每次构建都自动递增版本号造成版本污染；版本号改为由 `make update-version` 按需手动递增 patch，Makefile help 补充了该命令的用法说明。
- `scripts/update_version.py` 字符串引号与格式统一，便于 ruff format 稳定输出。

## [0.3.0] - 2026-05-02

### ⚠️ 升级须知（必读）
- **Vault 格式由 v4 升级到 v5（不向后兼容）**：KDF 由 PBKDF2-HMAC-SHA256 切换为 **Argon2id**。**请先用 0.2.x 将现有 `.zmb` 导出为 Excel，升级到 0.3.0 后再从 Excel 导入**；v3 `.gl` 文件依旧被拒绝。
- 0.2.1 ~ 0.2.8 为累计 bugfix 发布，未单独维护 changelog 条目，详情参考 git 历史。

### Experimental — Browser Fill Bridge (POC, opt-in, **not covered by stability guarantees**)
> ⚠️ Endpoints, request/response shapes and the token-file layout may change or be removed at any time. The `zhmm.browser_bridge` package will be deprecated and eventually removed once the stable path (KeePassXC-Browser protocol: X25519 + libsodium + Native Messaging) lands. Do not build long-term workflows on top of this POC.

- New `zhmm.browser_bridge` package implementing **Solution C** (local loopback HTTP + user-script) for browser autofill. **Disabled by default**; enable with `ZHMM_BROWSER_BRIDGE=1` before launching the GUI.
  - Binds to `127.0.0.1` on a random port; per-launch random 64-hex Bearer Token written to `~/.zhmm/browser_bridge.json` (0600), removed on app exit.
  - Endpoints: `GET /ping` (unauth, health), `POST /candidates` (auth, returns `userID/url/desc/has_totp` — **no passwords**), `POST /fill` (auth, requires a Qt approval dialog per request; returns userID + password + optional TOTP code).
  - Strict origin validation: `scheme://host[:port]` only, hostname-exact match against the entry's `url` (case-insensitive) — `example.com` and `exmple.com` are treated as distinct.
  - Approval dialog defaults focus to **「拒绝」** to avoid spacebar/Enter mis-approval, shows origin alongside the entry URL, offers an opt-in 5-minute trust window.
  - Response headers intentionally omit `Access-Control-Allow-Origin`, forcing the user script to use `GM_xmlhttpRequest` so arbitrary web pages cannot hit the bridge via `fetch()`.
  - Tampermonkey/Violentmonkey user script at `docs/browser_fill/zhmm-fill.user.js` — floating "zhmm" button on any page with a `<input type="password">`, candidate picker when multiple matches, auto-fill of username / password / TOTP fields. Setup guide: [`docs/browser_fill/README.md`](docs/browser_fill/README.md).
  - Clean-shutdown hook added to `AppWindow.closeEvent`; stopping the bridge erases the token file and clears the trust cache.
  - **User script v0.2.0**: dropped `@noframes` so the FAB also appears on sites whose login form lives in an iframe (e.g. `mail.qq.com` → `xui.ptlogin2.qq.com`); added multi-step-login auto-refill via `sessionStorage`-cached entry id (3-minute TTL, id only — no plaintext password cached) so the second page of a two-step flow (account → password) re-triggers `/fill` without another manual click; tightened password-field visibility detection to avoid false FAB mounts on hidden inputs; throttled MutationObserver callbacks (150 ms) to avoid CPU spikes on SPA churn.
  - **User script + server v0.3.0**: iframe-login origin matching now succeeds when the vault URL matches *any* ancestor origin. The user script sends the current origin plus `location.ancestorOrigins` as `frame_origins: string[]`; the server (`/candidates` & `/fill`) accepts an optional `frame_origins` array (max 16, each format-validated) and matches the entry's `url` against *any* origin in the list. The approval dialog still shows the specific matched origin, and the 5-minute trust cache covers all origins involved. User script also (1) relaxed FAB mount conditions — now also triggers on `autocomplete="username|email|current-password|new-password"` or login-path URL keywords (`login/signin/auth/account/passport`) plus a visible text input, so account-first multi-step logins (qoder.com, Google, 飞书) can trigger the FAB on the account page; (2) replaced `GM_notification` with an in-page toast for feedback (GM_notification is unreliable inside cross-origin iframes), with the toast showing all attempted origins when candidates come back empty so users can fix the vault `url` field.
  - **Multi-URL entry support** (server-only, zero data-format change): a single vault entry's `url` field can now hold **multiple URLs separated by whitespace / comma / semicolon / newline** (e.g. `cocos.com auth.cocos.com`); `origin_matches` splits on `[\s,;]+` and returns true if any of them has a hostname equal to the request origin. This handles the common case of one account having multiple login entry points (e.g. `cocos.com` + `auth.cocos.com`, `example.com` + `accounts.example.com`) without falling back to fuzzy parent/child-domain matching — every host must be explicitly listed by the user, which preserves the anti-phishing guarantee (`github.com` ↔ `pages.github.com` are still treated as distinct trust boundaries unless the user opts in). Single-URL entries behave identically to before; no migration needed.
  - Positioned as a POC to validate UX; the stable path forward is the KeePassXC-Browser protocol (X25519 + libsodium) — documented in the setup README.

### Documented
- README / SECURITY.md now explicitly document two long-existing safety features that were previously undocumented (or incorrectly described as missing):
  - **Auto-lock**: GUI returns to the login page and releases in-memory entries (`main_widget.deleteLater()`) when the window has been inactive for the user-configured duration (Settings → General → 自动锁定时间). Detection is based on `QWidget.isActiveWindow()` — it does not monitor mouse/keyboard, so a foreground-but-idle window will not trigger the lock.
  - **Clipboard auto-clear**: both password and TOTP code copies are wiped from the clipboard after 10 seconds; TOTP secrets never enter the clipboard.
- Corrected SECURITY.md "Known Limitations" entry that previously claimed no auto-lock existed.

### Added — TOTP 2FA
- **Built-in TOTP (time-based one-time password) support** covering both standard and Chinese SM variants:
  - Full **RFC 6238 / RFC 4226** implementation with `HMAC-SHA1 / SHA256 / SHA512`.
  - **SM3-TOTP extension** (algorithm name `SM3`) reusing the existing SM3 implementation — a zhmm-private variant for SM-compliance scenarios.
  - Accepts both raw Base32 secrets (tolerant of spaces, mixed case, missing padding) and `otpauth://` URIs (algo / digits / period auto-filled on paste).
- **GUI**
  - `PasswordEntry` gains four new fields: `totp_secret` (Base32), `totp_algo` (`SHA1|SHA256|SHA512|SM3`), `totp_digits` (default 6), `totp_period` (default 30).
  - Add / edit dialog shows a collapsible TOTP group box with live code preview and one-click `otpauth://` parsing.
  - Password table gains a new **「动态码 / TOTP」** column (index 5); the column refreshes every 1 second and shows `code  Ns remaining`. Click to copy to clipboard (cleared after 10 s).
- **CLI**
  - New `--totp <record_id>` flag on `zhmm-cli` prints the current code and remaining seconds for a given entry. The secret itself is never printed.
- **Excel export** explicitly **strips the TOTP secret**; only `totp_algo / totp_digits / totp_period` are written. Old `.xlsx` files without the new columns remain importable (loose header validation on the original 9 core columns).
- 33 new unit tests in `tests/test_core_totp.py`, including all 18 RFC 6238 official test vectors (SHA1 / SHA256 / SHA512) and SM3 self-consistency / boundary cases.

### Notes
- **TOTP is not a second factor against `.zmb` theft.** Secrets live inside the vault and are protected by the same Argon2id + SM4-CBC + HMAC-SM3 stack as passwords. For true out-of-band 2FA, use a hardware token or a separate authenticator app.
- **`SM3-TOTP` is a zhmm-private extension** and is not recognized by Google / Microsoft / 1Password authenticators. Do not dual-register such secrets with third-party apps.
- CLI *creating / editing* TOTP fields is intentionally deferred to the GUI; `--totp` only performs read-side verification.

### ⚠️ Breaking Changes
- **Vault format upgraded to v5**: KDF switched from PBKDF2-HMAC-SHA256 (v4) to **Argon2id** (2015 PHC winner, memory-hard). Header now embeds `m_cost / t_cost / p_cost` (each 4 bytes, big-endian) so future strength tuning won't require another format bump. **Old v4 `.zmb` files are not compatible** — export to Excel first, then re-import. v3 `.gl` files remain rejected.
- Header length grows from 37 B to 49 B; minimum blob overhead grows accordingly.

### Added
- `argon2-cffi (>=23.1.0)` dependency for Argon2id KDF (C implementation).
- Argon2id defaults: `m=64 MiB, t=3, p=1` (stronger than OWASP 2024 baseline `m=19 MiB, t=2, p=1`). Single derivation ≈ 100-500 ms on modern desktops.
- Range check on Argon2 parameters read from blob (`m ≤ 512 MiB, t ≤ 100, p ≤ 64`) to reject malicious vault files that would otherwise allocate gigabytes of memory.
- New tests covering: v4 blob rejection, Argon2 parameter tampering detection, out-of-range parameter rejection, and cross-parameter decryption (old params embedded in blob still decrypt after default upgrade).

### Changed
- `core/crypto.py`: full rewrite of `_derive_key` to use `argon2.low_level.hash_secret_raw` with `Argon2Type.ID`. Public API (`Vault.seal / Vault.open`) unchanged.
- Test suite: `tests/conftest.py` patches Argon2 parameters down to `m=8 KiB, t=1, p=1` during tests (saves several minutes across 146 test cases without changing behavior coverage).

### Security
- KDF no longer relies on PBKDF2; Argon2id's memory-hard design raises GPU/ASIC offline attack cost by orders of magnitude.
- Argon2 parameters are part of the HMAC-authenticated header, preventing parameter-downgrade attacks.

## [0.2.0] - 2025-10-XX

### ⚠️ Breaking Changes
- **New vault format (v4)**: vault files now use `.zmb` suffix with binary format (`ZHMM` magic, version byte `4`, HMAC-SM3 integrity tag). **Old `.gl` files from any previous version are not compatible** — export to Excel first, then re-import.
- **KDF now mixes account name + master password** (`account.utf8 + 0x00 + password.utf8`) via PBKDF2-HMAC-SHA256 (600 000 rounds, OWASP 2024 baseline). An empty or different account name results in a different key; the account name itself is **not** written to the vault.
- **CLI flag renamed**: `--openId` → `--account` (required, non-empty).
- **GUI login dialog**: the "OpenID" field is renamed to "账号名" and is required.
- **Cloud sync removed**: Tencent COS / OSS integration has been completely removed. Data is local-only.
- **Dependency cleanup**: removed `cos-python-sdk-v5`, `pycryptodomex`, `bcrypt`.

### Added
- **Anti-screenshot** (default on, toggleable in **Settings → General**): excludes `zhmm` windows from system screen capture on macOS (`NSWindow.sharingType = NSWindowSharingNone`) and Windows 10 2004+ (`SetWindowDisplayAffinity(WDA_EXCLUDE_FROM_CAPTURE)`, with `WDA_MONITOR` fallback). Applies to both the login dialog and the main window; takes effect instantly without restart. Linux is a no-op (no reliable system API). Cannot defend against camera re-shoot, capture cards, or VM screen grabs.
- New encryption engine (`core/crypto.py`): PBKDF2-HMAC-SHA256 (600 000 rounds) + SM4-CBC + HMAC-SM3, with account-in-KDF as an application-level constant salt against offline dictionary / rainbow attacks on weak passwords.
- `core/` business layer: `vault.py`, `password_service.py`, `backup_service.py`, `export_service.py`, `models.py`, `errors.py`.
- Unified entry point: `python -m zhmm` dispatches GUI / CLI based on arguments.
- Full type annotations for `core/`, `config/`, `utils/`, `cli/` (mypy --strict clean).
- Relaxed mypy configuration for `gui/`, `app/`, `widgets/`, `data/` (Qt signal/slot compatibility).
- `ruff` lint + format replacing flake8 + isort.
- CI: `ruff check` + `mypy` jobs as blocking quality gates.
- Pre-commit hooks: `ruff`, `ruff-format`, `mypy`.
- 135 pytest test cases covering crypto (including account-in-KDF invariants and v3-rejection), vault, services, and utilities.

### Changed
- Reorganized project directory: flat structure → `core/`, `config/`, `cli/`, `app/`, `gui/`, `widgets/`, `data/`, `utils/`.
- Renamed `qt_components/` → `widgets/`; `window_*` → `gui/*`.
- CLI entry: `zhmm-cli` now routes through `zhmm.cli.commands`.
- GUI entry: `zhmm` now routes through `zhmm.__main__`.
- File-list widget: the "OpenID" column is renamed to "账号" (still hidden by default).
- Backup service default suffix: `.gl` → `.zmb`.
- Version bumped to 0.2.0.

### Removed
- `cloud/` directory (6 files): `cloud_base.py`, `cloud_cos.py`, `cloud_oss.py`, `cloud_sync.py`, `file_local.py`.
- `window_setting/cloud_sync_handlers.py`, `window_setting/credentials_input_dialog_cos.py`.
- `sm_util.py`, `data/sm_crypto.py` (replaced by `core/crypto.py`).
- Legacy flat-file modules: `cmd_main.py`, `cmd_ui.py`, `ui_app.py`, `ui_main.py`, `ui_config.py`, `ui_defined.py`, etc.
- Legacy v3 vault support (PBKDF2-HMAC-SM3, password-only KDF) — no fallback read path.

### Security
- Eliminated hardcoded salt constants previously used in CLI password hashing.
- KDF upgraded to PBKDF2-HMAC-SHA256 at 600 000 iterations (OWASP 2024 recommended minimum), with account name mixed into the input material as an application-level constant salt.
- Added HMAC-SM3 authentication tag to vault files, preventing silent tampering.
- Vault version is now part of the HMAC-authenticated header, preventing downgrade attacks.

### Fixed
- CLI and GUI now share the same key derivation path (previously divergent).

## [0.1.4] - 2025-09-14

Initial public version, carried over from the pre-open-source tree:

- PyQt6 GUI for managing password entries (`zhmm`).
- `argparse`-based CLI (`zhmm-cli`) supporting search / create / modify / delete / export.
- SM3 key derivation + SM4 data encryption for the `.gl` vault format.
- Tencent COS cloud-sync with locally-encrypted credentials (Fernet + PBKDF2).
- Excel (xlsx) import / export.
- Light / dark theme switching.
- PyInstaller packaging for macOS / Windows / Linux.

[Unreleased]: https://github.com/Lioesquieu/zhmm/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/Lioesquieu/zhmm/compare/v0.2.8...v0.3.0
[0.2.0]: https://github.com/Lioesquieu/zhmm/compare/v0.1.4...v0.2.0
[0.1.4]: https://github.com/Lioesquieu/zhmm/releases/tag/v0.1.4
