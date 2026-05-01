#!/bin/bash
# 一次性批量替换：旧 import 路径 → 新 import 路径
# 目标：zhmm/ 和 tests/ 下所有 .py 文件

set -euo pipefail

BASE="$(cd "$(dirname "$0")/.." && pwd)"
cd "$BASE"

# 注意：顺序很关键 —— 长路径在前，短路径在后
# qt_components
find zhmm tests -name "*.py" -print0 | xargs -0 sed -i '' \
    -e 's|zhmm\.qt_components\.base_window|zhmm.widgets.base_window|g' \
    -e 's|zhmm\.qt_components\.dialog|zhmm.widgets.dialog|g' \
    -e 's|zhmm\.qt_components\.drag_drop_button|zhmm.widgets.drag_drop_button|g' \
    -e 's|zhmm\.qt_components\.plain_text_edit|zhmm.widgets.plain_text_edit|g' \
    -e 's|zhmm\.qt_components|zhmm.widgets|g'

# ui_*.py
find zhmm tests -name "*.py" -print0 | xargs -0 sed -i '' \
    -e 's|zhmm\.ui_main|zhmm.gui.main_window|g' \
    -e 's|zhmm\.ui_decrypt_data|zhmm.gui.decrypt_data_view|g' \
    -e 's|zhmm\.ui_app|zhmm.app.gui_app|g' \
    -e 's|zhmm\.ui_defined|zhmm.config.constants|g' \
    -e 's|zhmm\.ui_config|zhmm.config.paths|g'

# ui/ 子目录
find zhmm tests -name "*.py" -print0 | xargs -0 sed -i '' \
    -e 's|zhmm\.ui\.file_list_widget|zhmm.gui.file_list_widget|g' \
    -e 's|zhmm\.ui\.welcome_widget|zhmm.gui.welcome_widget|g'

# theme_manager
find zhmm tests -name "*.py" -print0 | xargs -0 sed -i '' \
    -e 's|zhmm\.theme_manager|zhmm.gui.theme|g'

# window_login / window_password / window_setting
find zhmm tests -name "*.py" -print0 | xargs -0 sed -i '' \
    -e 's|zhmm\.window_login\.login_window|zhmm.gui.login.login_window|g' \
    -e 's|zhmm\.window_password\.password_window|zhmm.gui.password.window|g' \
    -e 's|zhmm\.window_password\.add_password_dialog|zhmm.gui.password.add_dialog|g' \
    -e 's|zhmm\.window_password\.random_password_dialog|zhmm.gui.password.random_dialog|g' \
    -e 's|zhmm\.window_password\.password_table_models|zhmm.gui.password.table_models|g' \
    -e 's|zhmm\.window_password\.password_operations|zhmm.gui.password.operations|g' \
    -e 's|zhmm\.window_setting\.setting_window|zhmm.gui.settings.window|g' \
    -e 's|zhmm\.window_setting\.backup_list_dialog|zhmm.gui.settings.backup_list_dialog|g' \
    -e 's|zhmm\.window_setting\.backup_settings|zhmm.gui.settings.backup_settings|g' \
    -e 's|zhmm\.window_setting\.import_export_handlers|zhmm.gui.settings.import_export_handlers|g'

# cmd_main / cmd_ui
find zhmm tests -name "*.py" -print0 | xargs -0 sed -i '' \
    -e 's|zhmm\.cmd_main|zhmm.cli.commands|g' \
    -e 's|zhmm\.cmd_ui|zhmm.cli.interactive|g'

# app_config / app_setting
find zhmm tests -name "*.py" -print0 | xargs -0 sed -i '' \
    -e 's|zhmm\.app_config|zhmm.config.app_config|g' \
    -e 's|zhmm\.app_setting|zhmm.config.settings|g'

echo "import rename done."
