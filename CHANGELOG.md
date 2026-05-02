# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
