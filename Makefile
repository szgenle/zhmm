.PHONY: help install run run-gui run-cmd debug build-app build-cmd build-all clean clean-build clean-dist env-info format lint test pre-commit

# 可选的 pip 镜像源。默认为空（使用官方 PyPI）。
# 指定方式: make build-app PIP_INDEX=https://pypi.tuna.tsinghua.edu.cn/simple/
PIP_INDEX ?=
PIP_INDEX_ARG = $(if $(PIP_INDEX),-i $(PIP_INDEX),)

# 默认目标：显示帮助信息
help:
	@echo "可用的 Make 命令："
	@echo "  make install       - 安装项目依赖"
	@echo "  make run           - 运行GUI应用程序"
	@echo "  make run-gui       - 运行GUI应用程序（同 run）"
	@echo "  make run-cmd       - 运行命令行应用程序"
	@echo "  make debug         - 使用调试模式运行应用程序"
	@echo "  make build-app     - 构建GUI应用程序"
	@echo "  make build-cmd     - 构建命令行应用程序"
	@echo "  make build-all     - 构建所有应用程序"
	@echo "  make clean         - 清理所有构建文件"
	@echo "  make clean-build   - 清理构建缓存"
	@echo "  make clean-dist    - 清理分发文件"
	@echo "  make env-info      - 显示Poetry虚拟环境信息"
	@echo "  make format        - 格式化代码（使用isort）"
	@echo "  make lint          - 代码检查（使用flake8）"
	@echo "  make test          - 运行 pytest 单元测试"
	@echo "  make pre-commit    - 运行pre-commit检查"
	@echo "  make update-version - 递增 patch 版本号（仅发版时手动调用）"
	@echo ""
	@echo "可选变量："
	@echo "  PIP_INDEX=<url>    - pip 镜像源（默认使用官方 PyPI）"

# 安装依赖
install:
	@echo "安装项目依赖..."
	poetry install
	@echo "依赖安装完成！"

# 运行GUI应用程序
run:
	@echo "启动GUI应用程序..."
	poetry run python -m zhmm.main

run-gui: run

# 运行命令行应用程序
run-cmd:
	@echo "启动命令行应用程序..."
	poetry run python -m zhmm cli

# 调试模式运行
debug:
	@echo "使用调试模式启动应用程序..."
	poetry run python -m pdb -m zhmm.main

# 更新版本号（仅在发版时手动调用：`make update-version`；不挂到 build-* 依赖，避免每次打包都污染版本号）
update-version:
	@echo "更新版本号..."
	poetry run python scripts/update_version.py

# 构建GUI应用程序
# 说明：必须使用 `poetry run python -m PyInstaller`，否则 `poetry run pyinstaller`
# 在 venv 里没装 pyinstaller 时会回落到 PATH 上的系统 pyinstaller（如 Homebrew 版），
# 其使用的 Python 解释器看不到 venv 里的 PyQt6，导致打出来的 .app 启动时
# `ModuleNotFoundError: No module named 'PyQt6'`。
build-app: clean-build
	@echo "构建GUI应用程序..."
	poetry run pip install pyinstaller certifi $(PIP_INDEX_ARG)
	poetry run python -m PyInstaller --onefile --windowed --name "zhmm" \
		--osx-bundle-identifier "com.szgenle.zhmm" \
		--icon=myicon.icns \
		--collect-all certifi \
		--collect-all PyQt6 \
		--add-data "zhmm/resources:resources" \
		zhmm/__main__.py \
		--paths .
	@echo "GUI应用程序构建完成！"

# 构建命令行应用程序（--onedir：避免 --onefile 每次启动的自解压耗时，启动更快）
build-cmd: clean-build
	@echo "构建命令行应用程序..."
	poetry run pip install pyinstaller certifi $(PIP_INDEX_ARG)
	poetry run python -m PyInstaller --onedir --name "zhmm_cmd" \
		--osx-bundle-identifier "com.szgenle.zhmm" \
		--icon=myicon.icns \
		--collect-all certifi \
		--exclude-module PyQt6 \
		--exclude-module PyQt6.QtCore \
		--exclude-module PyQt6.QtGui \
		--exclude-module PyQt6.QtWidgets \
		--exclude-module PyQt6.QtSvg \
		--exclude-module zhmm.gui \
		--exclude-module zhmm.app.gui_app \
		zhmm/cli/commands.py \
		--paths .
	@echo "命令行应用程序构建完成！产物目录：dist/zhmm_cmd/"

# 构建所有应用程序
build-all: clean-build
	@echo "构建所有应用程序..."
	poetry run pip install pyinstaller certifi $(PIP_INDEX_ARG)
	@echo "构建GUI应用程序..."
	poetry run python -m PyInstaller --onefile --windowed --name "zhmm" \
		--osx-bundle-identifier "com.szgenle.zhmm" \
		--icon=myicon.icns \
		--collect-all certifi \
		--collect-all PyQt6 \
		--add-data "zhmm/resources:resources" \
		zhmm/__main__.py \
		--paths .
	@echo "构建命令行应用程序..."
	poetry run python -m PyInstaller --onedir --name "zhmm_cmd" \
		--osx-bundle-identifier "com.szgenle.zhmm" \
		--icon=myicon.icns \
		--collect-all certifi \
		--exclude-module PyQt6 \
		--exclude-module PyQt6.QtCore \
		--exclude-module PyQt6.QtGui \
		--exclude-module PyQt6.QtWidgets \
		--exclude-module PyQt6.QtSvg \
		--exclude-module zhmm.gui \
		--exclude-module zhmm.app.gui_app \
		zhmm/cli/commands.py \
		--paths .
	@echo "所有应用程序构建完成！"

# 清理构建缓存
clean-build:
	@echo "清理构建缓存..."
	rm -rf build
	rm -rf *.spec

# 清理分发文件
clean-dist:
	@echo "清理分发文件..."
	rm -rf dist

# 清理所有构建文件
clean: clean-build clean-dist
	@echo "清理Python缓存文件..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@echo "清理完成！"

# 显示Poetry虚拟环境信息
env-info:
	@echo "Poetry虚拟环境信息："
	poetry env info

# 格式化代码
format:
	@echo "格式化代码..."
	poetry run ruff format zhmm/ tests/
	poetry run ruff check --fix zhmm/ tests/
	@echo "代码格式化完成！"

# 代码检查
lint:
	@echo "运行代码检查..."
	poetry run ruff check zhmm/ tests/
	@echo "代码检查完成！"

# 运行测试
test:
	@echo "运行单元测试..."
	poetry run pytest
	@echo "测试完成！"

# 运行pre-commit检查
pre-commit:
	@echo "运行pre-commit检查..."
	poetry run pre-commit run --all-files
	@echo "pre-commit检查完成！"
