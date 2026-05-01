<h1 align="center">🔐 zhmm</h1>

<p align="center">
  A local-first password manager powered by <b>Chinese SM cryptography (SM2 / SM3 / SM4)</b>.<br/>
  Ships both a PyQt6 GUI and a CLI, with optional encrypted cloud sync via Tencent COS.
</p>

<p align="center">
  <a href="https://github.com/Lioesquieu/zhmm/actions"><img src="https://img.shields.io/github/actions/workflow/status/Lioesquieu/zhmm/ci.yml?branch=main&label=CI" alt="CI"></a>
  <a href="https://github.com/Lioesquieu/zhmm/releases"><img src="https://img.shields.io/github/v/release/Lioesquieu/zhmm?include_prereleases" alt="Release"></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white" alt="Python"></a>
  <a href="https://pypi.org/project/PyQt6/"><img src="https://img.shields.io/badge/GUI-PyQt6-41CD52?logo=qt&logoColor=white" alt="PyQt6"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License"></a>
  <a href="README.md">简体中文</a>
</p>

---

## ✨ Features

- 🔒 **Chinese SM crypto**: SM3 for key derivation, SM4 for data encryption. Master key never touches disk.
- 💻 **Dual form factor**: one core, two UIs — **PyQt6 GUI** and **CLI (argparse)**.
- ☁️ **Local-first, optional cloud sync**: encrypted data stays local; sync to Tencent COS if you want.
- 📦 **Single-file vault**: one `.gl` file *is* your vault — easy to back up and migrate.
- 📝 **Import / export**: full Excel (xlsx) round-tripping.
- 🎨 **Themes**: built-in light / dark themes.
- 🧰 **Batteries included**: PyInstaller recipes for macOS / Windows / Linux.

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
poetry run python -m zhmm.main           # launch GUI
poetry run python -m zhmm.cmd_main ...   # launch CLI
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
poetry run python -m zhmm.main
# or, after building
open /Applications/zhmm.app
```

On first launch:

1. Enter your **OpenID** (any stable unique identifier: email, phone, etc.) and a **master password**.
2. Add entries (site, account, password, notes) in the main window.
3. Configure cloud sync and backup strategy in **Settings** (optional).

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
├── cloud/          # cloud-sync abstraction (base / cos / oss / sync / local)
├── data/           # crypto layer (sm_crypto / sm_data_manager / sm_data_types)
├── qt_components/  # shared Qt widgets
├── ui/             # UI widgets
├── utils/          # utilities (logging, dates, network, tables, JSON, ...)
├── window_login/   # login window
├── window_password/# password main window
├── window_setting/ # settings window
├── main.py         # GUI entry point
├── cmd_main.py     # CLI entry point
├── app_config.py   # app config (Fernet + PBKDF2 at rest)
├── app_setting.py  # QSettings wrapper
└── backup_manager.py
```

**Core dependencies**

| Area           | Library                                                  |
|----------------|----------------------------------------------------------|
| GUI            | `PyQt6`                                                  |
| SM crypto      | `gmssl` (SM2/SM3/SM4)                                    |
| General crypto | `cryptography` (Fernet/PBKDF2), `pycryptodomex`, `bcrypt`|
| Cloud storage  | `cos-python-sdk-v5`                                      |
| Excel          | `openpyxl`                                               |
| Packaging      | `PyInstaller`                                            |

---

## 🔒 Security

> This project handles password data. Please read before use.

- **Key derivation**: the master password is hashed with SM3 to derive the encryption key. **The master password is never persisted.**
- **Data encryption**: every password entry is SM4-encrypted inside the `.gl` file.
- **Config encryption**: cloud credentials are encrypted at rest with `Fernet (PBKDF2-HMAC-SHA256 + random salt)`.
- **Data in cloud**: only the **already-encrypted `.gl` file** is uploaded — the cloud provider cannot decrypt it.
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
make format         # isort
make lint           # flake8
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
2. Run `make format && make lint` to keep style consistent.
3. Add tests where applicable.

---

## 📄 License

[MIT](LICENSE).

---

## 🙏 Acknowledgements

- [gmssl-python](https://github.com/duanhongyi/gmssl) — Chinese SM crypto in Python
- [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) — GUI framework
- All contributors 💙
