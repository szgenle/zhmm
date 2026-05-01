# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Open-source baseline: MIT `LICENSE`, bilingual `README`, `CONTRIBUTING`, `CODE_OF_CONDUCT`, `SECURITY`.
- GitHub issue / PR templates and CI workflows (lint + pytest + release builds).
- `pytest` test scaffold and baseline test cases.
- Richer `pyproject.toml` metadata: keywords, classifiers, project URLs.

### Changed
- Hardened `.gitignore` to exclude `*.gl` vault files, local configs and certificates.
- `mv_cmd.sh` / `mv_app.sh` now use `set -euo pipefail` and overridable targets.

### Security
- Removed hardcoded personal contact from `pyproject.toml` and stripped author-identifying
  headers from several source files.

## [0.1.4] - 2025-09-14

Initial public version, carried over from the pre-open-source tree:

- PyQt6 GUI for managing password entries (`zhmm`).
- `argparse`-based CLI (`zhmm-cli`) supporting search / create / modify / delete / export.
- SM3 key derivation + SM4 data encryption for the `.gl` vault format.
- Tencent COS cloud-sync with locally-encrypted credentials (Fernet + PBKDF2).
- Excel (xlsx) import / export.
- Light / dark theme switching.
- PyInstaller packaging for macOS / Windows / Linux.

[Unreleased]: https://github.com/Lioesquieu/zhmm/compare/v0.1.4...HEAD
[0.1.4]: https://github.com/Lioesquieu/zhmm/releases/tag/v0.1.4
