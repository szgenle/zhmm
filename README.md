<h1 align="center">🔐 zhmm</h1>

<p align="center">
  基于 <b>国密算法（SM2 / SM3 / SM4）</b> 的本地优先账号密码管理器<br/>
  支持 PyQt6 图形界面、命令行两种形态，并可对接腾讯云 COS 做加密备份同步。
</p>

<p align="center">
  <a href="https://github.com/Lioesquieu/zhmm/actions"><img src="https://img.shields.io/github/actions/workflow/status/Lioesquieu/zhmm/ci.yml?branch=main&label=CI" alt="CI"></a>
  <a href="https://github.com/Lioesquieu/zhmm/releases"><img src="https://img.shields.io/github/v/release/Lioesquieu/zhmm?include_prereleases" alt="Release"></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white" alt="Python"></a>
  <a href="https://pypi.org/project/PyQt6/"><img src="https://img.shields.io/badge/GUI-PyQt6-41CD52?logo=qt&logoColor=white" alt="PyQt6"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License"></a>
  <a href="README_EN.md">English</a>
</p>

---

## ✨ 特性

- 🔒 **国密加密**：使用 SM3 做密钥派生、SM4 做数据加密，密钥永不落盘
- 💻 **双形态**：同一套核心，提供 **GUI（PyQt6）** 与 **CLI（argparse）** 两种使用方式
- ☁️ **本地优先 + 可选云同步**：数据加密后本地存储，可选择性地同步到腾讯云 COS
- 📦 **单文件数据格式**：一个 `.gl` 文件即完整密库，便于备份、迁移
- 📝 **支持导入/导出**：支持 Excel（xlsx）导入导出
- 🎨 **主题切换**：内置浅色/深色主题
- 🧰 **开箱即用**：提供 PyInstaller 打包脚本，一键构建 macOS / Windows / Linux 发行版

---

## 📦 安装

### 方式一：下载预编译二进制（推荐普通用户）

到 [Releases](https://github.com/Lioesquieu/zhmm/releases) 页面下载对应平台的安装包：

- macOS：`zhmm.app.zip`
- Windows：`zhmm.exe`
- Linux：`zhmm`（x86_64）

### 方式二：从源码运行（推荐开发者）

```bash
git clone https://github.com/Lioesquieu/zhmm.git
cd zhmm
poetry install
poetry run python -m zhmm.main           # 启动 GUI
poetry run python -m zhmm.cmd_main ...   # 启动 CLI
```

### 方式三：pip 安装

```bash
pip install zhmm                         # 从 PyPI（待发布）
# 或从 GitHub 最新版：
pip install git+https://github.com/Lioesquieu/zhmm.git
```

---

## 🚀 快速开始

### GUI 模式

```bash
poetry run python -m zhmm.main
# 或打包后
open /Applications/zhmm.app
```

首次使用：

1. 在登录窗口输入 **OpenID**（任意稳定唯一标识均可，如邮箱、手机号）和 **主密码**
2. 进入主界面后新增条目（站点名、账号、密码、备注）
3. 可在「设置」中配置云同步凭据与备份策略

### CLI 模式

```bash
# 查询（search / find）
zhmm-cli -i ~/zhmm.gl --openId you@example.com -s github

# 新增
zhmm-cli -i ~/zhmm.gl --openId you@example.com -n

# 修改
zhmm-cli -i ~/zhmm.gl --openId you@example.com -m

# 删除
zhmm-cli -i ~/zhmm.gl --openId you@example.com -d <record_id>

# 导出
zhmm-cli -i ~/zhmm.gl --openId you@example.com -e ~/backup.xlsx

# 简单（只读）模式
zhmm-cli -i ~/zhmm.gl --openId you@example.com --simple -s github
```

> 密码默认从 stdin 隐式读取；也可通过 `--pwd` 显式传入（⚠️ 会被 shell history 记录）。
> 完整参数列表见 `zhmm-cli --help`。

---

## 🏗 技术架构

```
zhmm/
├── cloud/          # 云同步抽象（base / cos / oss / sync / local）
├── data/           # 加密层（sm_crypto / sm_data_manager / sm_data_types）
├── qt_components/  # 通用 Qt 组件
├── ui/             # UI Widgets
├── utils/          # 工具函数（日志/日期/网络/表格/JSON 等）
├── window_login/   # 登录窗口
├── window_password/# 密码主界面
├── window_setting/ # 设置窗口
├── main.py         # GUI 入口
├── cmd_main.py     # CLI 入口
├── app_config.py   # 应用配置（Fernet + PBKDF2 加密落盘）
├── app_setting.py  # QSettings 封装
└── backup_manager.py
```

**核心依赖**

| 领域       | 库                                 |
|----------|-----------------------------------|
| GUI      | `PyQt6`                           |
| 国密加密    | `gmssl` (SM2/SM3/SM4)              |
| 通用加密    | `cryptography` (Fernet/PBKDF2), `pycryptodomex`, `bcrypt` |
| 云存储     | `cos-python-sdk-v5`               |
| Excel    | `openpyxl`                        |
| 打包      | `PyInstaller`                     |

---

## 🔒 安全说明

> 本项目处理用户密码数据，请在使用前仔细阅读。

- **密钥派生**：用户主密码经 SM3 哈希派生成加密密钥，**主密码永不持久化**
- **数据加密**：所有密码条目以 SM4 加密写入 `.gl` 文件
- **配置加密**：云存储凭据经 `Fernet (PBKDF2-HMAC-SHA256 + 随机盐)` 加密本地落盘
- **云上数据**：同步到云端的是**已加密的 `.gl` 文件**，云服务商无法解密
- **`.gl` 文件**：等同于密库，请妥善保管，建议多地备份
- **已知限制**：详见 [SECURITY.md](SECURITY.md)

发现安全漏洞请通过 [SECURITY.md](SECURITY.md) 中的方式进行**私下**披露，请勿直接提 Issue。

---

## 🧑‍💻 开发

常用命令封装在 `Makefile` 中：

```bash
make install        # 安装依赖
make run            # 启动 GUI
make run-cmd        # 启动 CLI
make debug          # pdb 调试
make format         # isort 格式化
make lint           # flake8 检查
make pre-commit     # 运行 pre-commit
make build-app      # 打包 GUI
make build-cmd      # 打包 CLI
make build-all      # 打包全部
make clean          # 清理
```

### 运行测试

```bash
poetry run pytest                 # 运行所有测试
poetry run pytest --cov=zhmm      # 带覆盖率
```

### 版本号管理

版本号在构建时由 [`scripts/update_version.py`](scripts/update_version.py) 自动写入，关于对话框会展示当前版本。

---

## 🤝 贡献

欢迎 Issue / PR，提交前请：

1. 阅读 [CONTRIBUTING.md](CONTRIBUTING.md) 与 [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)
2. 执行 `make format && make lint` 保证代码风格一致
3. 为改动编写测试（如适用）

---

## 📄 许可证

本项目采用 [MIT License](LICENSE)。

---

## 🙏 致谢

- [gmssl-python](https://github.com/duanhongyi/gmssl) — 国密算法 Python 实现
- [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) — GUI 框架
- 所有贡献者 💙
