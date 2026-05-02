# 贡献指南 / Contributing

感谢你考虑为 **zhmm** 贡献代码！本指南帮助你快速上手。
*English speakers: the sections below are concise enough to read with your browser's translator. PRs welcome in either 中文 or English.*

---

## 🐛 报告 Bug

1. 先在 [Issues](https://github.com/Lioesquieu/zhmm/issues) 搜索是否已有相同问题
2. 若无，使用 **Bug Report** 模板新建 Issue，清楚给出：
   - 复现步骤、期望 vs 实际
   - 操作系统、Python 版本、zhmm 版本
   - 相关日志（`.log/` 目录下，**请先脱敏**）

> ⚠️ **不要**在 Issue 中贴真实账号/密码/云凭据。
> ⚠️ 若涉及安全漏洞，请改走 [SECURITY.md](SECURITY.md) 的私下披露流程。

## 💡 提交功能建议

使用 **Feature Request** 模板，重点描述 *用户场景* 而非具体实现。

## 🧑‍💻 提交代码（Pull Request）

### 环境准备

```bash
git clone https://github.com/Lioesquieu/zhmm.git
cd zhmm
poetry install
poetry run pre-commit install      # 首次必做
```

### 工作流

1. Fork 本仓库，在你的 fork 上基于 `main` 切分支：`git checkout -b feat/my-change`
2. 提交前本地自检：
   ```bash
   make format       # ruff format + ruff check --fix
   make lint         # ruff check
   poetry run pytest # 测试
   ```
3. Commit 信息建议遵循 [Conventional Commits](https://www.conventionalcommits.org/)：
   - `feat: 新增 xxx`
   - `fix: 修复 xxx`
   - `docs: 更新文档`
   - `refactor: 重构 xxx`
   - `test: 补充测试`
   - `chore: 其它杂项`
4. 推到你的 fork，针对上游 `main` 发起 PR，填写 PR 模板
5. 耐心等待 Review，根据反馈修改

### 代码规范

- 遵循 **PEP 8**，`ruff` 已配置为 lint + format 工具
- 行宽 120，字符串优先使用双引号
- 公共 API 加类型注解与 docstring（`core/`、`config/`、`utils/`、`cli/` 模块要求 mypy --strict 通过）
- 日志统一走 `zhmm.utils.log.logger`，不要 `print` 到 stdout
- 涉及加密/安全逻辑的改动，请在 PR 描述中明确说明

### 项目目录结构

```
zhmm/
├── core/           # 加密引擎、数据模型、业务服务
├── config/         # 应用配置、QSettings、常量
├── cli/            # argparse 子命令与交互循环
├── app/            # GUI / CLI 入口装配
├── gui/            # PyQt6 界面（login / password / settings / theme）
├── widgets/        # 通用 Qt 组件
├── data/           # 数据管理
├── utils/          # 工具函数
├── __init__.py     # 版本号与包元信息
└── __main__.py     # python -m zhmm 统一入口
```

### 测试

- 新功能请在 `tests/` 下补测试
- 跑单个测试：`poetry run pytest tests/test_xxx.py -k test_name`
- 覆盖率：`poetry run pytest --cov=zhmm --cov-report=term-missing`

## 📜 许可与所有权

你同意你的贡献在 [GPL-3.0 License](LICENSE) 下发布。你对自己的提交拥有完整版权或授权，且不包含任何他人作品未经授权的部分。

## 💬 行为准则

参与本项目即表示遵守 [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)。请保持友善、建设性、可包容。

---

再次感谢你的贡献！🎉
