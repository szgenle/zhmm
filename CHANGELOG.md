# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - Unreleased

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

[Unreleased]: https://github.com/Lioesquieu/zhmm/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/Lioesquieu/zhmm/compare/v0.1.4...v0.2.0
[0.1.4]: https://github.com/Lioesquieu/zhmm/releases/tag/v0.1.4
