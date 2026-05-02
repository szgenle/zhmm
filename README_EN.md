<h1 align="center">🔐 zhmm</h1>

<p align="center">
  A local-first password manager powered by <b>Chinese SM cryptography (SM3 / SM4)</b>.<br/>
  Ships both a PyQt6 GUI and a CLI. Single-file vault, batteries included.
</p>

<p align="center">
  <a href="https://github.com/Lioesquieu/zhmm/actions"><img src="https://img.shields.io/github/actions/workflow/status/Lioesquieu/zhmm/ci.yml?branch=main&label=CI" alt="CI"></a>
  <a href="https://github.com/Lioesquieu/zhmm/releases"><img src="https://img.shields.io/github/v/release/Lioesquieu/zhmm?include_prereleases" alt="Release"></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white" alt="Python"></a>
  <a href="https://pypi.org/project/PyQt6/"><img src="https://img.shields.io/badge/GUI-PyQt6-41CD52?logo=qt&logoColor=white" alt="PyQt6"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-GPL--3.0-blue.svg" alt="License"></a>
  <a href="README.md">简体中文</a>
</p>

---

## ✨ Features

- 🔒 **Chinese SM crypto**: PBKDF2-HMAC-SM3 key derivation (200 000 rounds) + SM4-CBC encryption + HMAC-SM3 integrity tag. Master key never touches disk.
- 💻 **Dual form factor**: one core, two UIs — **PyQt6 GUI** and **CLI (argparse)**.
- 📦 **Single-file vault**: one `.gl` file *is* your vault (binary format with magic, version, auth tag) — easy to back up and migrate.
- 📝 **Import / export**: full Excel (xlsx) round-tripping.
- 🎨 **Themes**: built-in light / dark themes.
- 🧰 **Batteries included**: PyInstaller recipes for macOS / Windows / Linux.
- 🛡 **CI quality gates**: ruff lint / mypy type check / pytest must all pass before merge.

---

## 📦 Installation

### Option 1 — Prebuilt binaries (recommended for end users)

Grab the latest artifacts from [Releases](https://github.com/Lioesquieu/zhmm/releases):

- macOS: `zhmm.app.zip`
- Windows: `zhmm.exe`
- Linux: `zhmm` (x86_64)

### Option 2 — From source (recommended for developers)

```bash
git clone https://github.com/Lioesquieu/zhmm.git
cd zhmm
poetry install
poetry run python -m zhmm                # launch GUI
poetry run python -m zhmm cli ...        # launch CLI
```

### Option 3 — pip

```bash
pip install zhmm                         # from PyPI (coming soon)
# or install the latest from GitHub:
pip install git+https://github.com/Lioesquieu/zhmm.git
```

---

## 🚀 Quickstart

### GUI

```bash
poetry run python -m zhmm
# or, after building
open /Applications/zhmm.app
```

On first launch:

1. Enter your **OpenID** (any stable unique identifier: email, phone, etc.) and a **master password**.
2. Add entries (site, account, password, notes) in the main window.
3. Configure backup strategy in **Settings** (optional).

### CLI

```bash
# Search
zhmm-cli -i ~/zhmm.gl --openId you@example.com -s github

# Create
zhmm-cli -i ~/zhmm.gl --openId you@example.com -n

# Modify
zhmm-cli -i ~/zhmm.gl --openId you@example.com -m

# Delete
zhmm-cli -i ~/zhmm.gl --openId you@example.com -d <record_id>

# Export
zhmm-cli -i ~/zhmm.gl --openId you@example.com -e ~/backup.xlsx

# Simple (read-only) mode
zhmm-cli -i ~/zhmm.gl --openId you@example.com --simple -s github
```

> Password is read from stdin by default. `--pwd` is supported but will be
> recorded in shell history — avoid it.
> See `zhmm-cli --help` for the full flag list.

---

## 🏗 Architecture

```
zhmm/
├── core/           # crypto engine, data models, business services (password/backup/export)
├── config/         # app configuration, QSettings, constants
├── cli/            # argparse sub-commands and interactive loop
├── app/            # GUI / CLI entry assembly
├── gui/            # PyQt6 views (login / password / settings / theme …)
├── widgets/        # reusable Qt widgets (BaseWindow / Dialog / DragDropButton …)
├── data/           # data management (SmData / SmDataTypes)
├── utils/          # utilities (logging, dates, network, tables, JSON, …)
├── __init__.py     # version and package metadata
└── __main__.py     # python -m zhmm unified entry (dispatches GUI / CLI)
```

**Core dependencies**

| Area           | Library                                                  |
|----------------|----------------------------------------------------------|
| GUI            | `PyQt6`                                                  |
| SM crypto      | `gmssl` (SM3/SM4)                                        |
| Config crypto  | `cryptography` (Fernet/PBKDF2)                           |
| Excel          | `openpyxl`                                               |
| Packaging      | `PyInstaller`                                            |

### 🔐 Encryption Design

The `.gl` vault file is protected by a pure Chinese SM algorithm stack:

| Stage | Algorithm | Details |
|-------|-----------|--------|
| Key derivation | **PBKDF2-HMAC-SM3** | 200 000 iterations, 16-byte random salt, derives 32-byte key |
| Encryption | **SM4-CBC** | 16-byte random IV, PKCS7 padding |
| Integrity | **HMAC-SM3** | Covers header + ciphertext, produces 32-byte auth tag |

File layout:

```
magic(4B="ZHMM") | ver(1B=3) | salt(16B) | iv(16B) | ciphertext(NB) | tag(32B)
```

- **magic**: lets the `file` command identify the file type
- **ver**: standalone version byte for future upgrades
- **tag**: covers header + ciphertext, preventing downgrade attacks and tampering

---

## 🔒 Security

> This project handles password data. Please read before use.

- **Key derivation**: the master password is processed through PBKDF2-HMAC-SM3 (200 000 rounds) to derive the encryption key. **The master password is never persisted.**
- **Data encryption**: every password entry is SM4-CBC encrypted inside the `.gl` file, with an HMAC-SM3 integrity tag.
- **Config encryption**: local application config is encrypted at rest with `Fernet (PBKDF2-HMAC-SHA256 + random salt)`.
- **`.gl` file**: treat it like your vault; back it up in multiple places.
- **Known limitations**: see [SECURITY.md](SECURITY.md).

Security vulnerabilities? Please **privately** disclose them per [SECURITY.md](SECURITY.md) — do **not** open a public issue.

---

## 🧑‍💻 Development

Common tasks are wired up in the `Makefile`:

```bash
make install        # install deps
make run            # launch GUI
make run-cmd        # launch CLI
make debug          # pdb debug
make format         # ruff format + ruff check --fix
make lint           # ruff check
make pre-commit     # run pre-commit hooks
make build-app      # build GUI bundle
make build-cmd      # build CLI bundle
make build-all      # build everything
make clean          # clean artifacts
```

### Tests

```bash
poetry run pytest                 # run all tests
poetry run pytest --cov=zhmm      # with coverage
```

### Versioning

Version strings are injected at build time by [`scripts/update_version.py`](scripts/update_version.py) and surfaced in the About dialog.

---

## 🤝 Contributing

Issues and PRs welcome! Before sending a PR:

1. Read [CONTRIBUTING.md](CONTRIBUTING.md) and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
2. Run `make format && make lint` to keep style consistent (powered by ruff).
3. Add tests where applicable.

---

## 📄 License

[GPL-3.0](LICENSE).

---

## 🙏 Acknowledgements

- [gmssl-python](https://github.com/duanhongyi/gmssl) — Chinese SM crypto in Python
- [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) — GUI framework
- All contributors 💙
