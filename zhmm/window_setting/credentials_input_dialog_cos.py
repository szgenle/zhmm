from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QLineEdit, QVBoxLayout

import zhmm


class CredentialsDialogCos(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("云存储凭证配置")
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)

        # 云存储凭证表单
        form_layout = QFormLayout()

        self.secret_id_edit = QLineEdit(zhmm.config.get("qcloud.secret_id", ""))
        form_layout.addRow("Secret ID:", self.secret_id_edit)

        self.secret_key_edit = QLineEdit(zhmm.config.get("qcloud.secret_key", ""))
        form_layout.addRow("Secret Key:", self.secret_key_edit)

        self.region_edit = QLineEdit(zhmm.config.get("qcloud.region", ""))
        form_layout.addRow("Region:", self.region_edit)

        self.bucket_edit = QLineEdit(zhmm.config.get("qcloud.bucket", ""))
        form_layout.addRow("Bucket:", self.bucket_edit)

        main_layout.addLayout(form_layout)

        # 对话框按钮（确定/取消）
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.save_credentials)
        button_box.rejected.connect(self.reject)
        main_layout.addWidget(button_box)

    def save_credentials(self):
        """保存云存储凭证并关闭对话框"""
        zhmm.config.set("qcloud.secret_id", self.secret_id_edit.text())
        zhmm.config.set("qcloud.secret_key", self.secret_key_edit.text())
        zhmm.config.set("qcloud.region", self.region_edit.text())
        zhmm.config.set("qcloud.bucket", self.bucket_edit.text())
        zhmm.config.save_config()
        self.accept()
