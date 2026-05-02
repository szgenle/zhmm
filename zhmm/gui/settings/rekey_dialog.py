#!/usr/bin/env python3
"""更换主密码（Re-key）对话框 + 后台 Worker。

交互流程：
    1. 用户输入当前密码、新密码、确认新密码。
    2. 当前密码用会话保存的 bcrypt hashpw 校验；新密码做非空/一致/非同值校验。
    3. 校验通过后启动 :class:`RekeyWorker` 线程：
       - 先用 ``BackupService`` 以 ``prefix="rekey"`` 生成保险备份；
       - 再调 ``VaultFile.rekey`` 原地换密；
       - 任一步失败即中止并把错误回传给 UI。
    4. 对话框展示 :class:`QProgressDialog`（不可取消、模态、indeterminate）。
    5. 成功回调由调用方（设置页）注入，负责刷新会话 / saved_files / config 密钥。
"""

from __future__ import annotations

from pathlib import Path

import bcrypt
from PyQt6.QtCore import QSize, Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QShowEvent
from PyQt6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

import zhmm
from zhmm.config.constants import ZhmmFileInfo
from zhmm.core.backup_service import BackupService
from zhmm.core.errors import CryptoError, StorageError
from zhmm.data.sm_data_manager import SmData
from zhmm.gui.texts import Rekey as RekeyText
from zhmm.utils import file_util
from zhmm.utils.anti_capture import apply_anti_capture
from zhmm.utils.log import logger
from zhmm.widgets.dialog import Dialog
from zhmm.widgets.eye_icon import EYE_CLOSED_SVG, EYE_OPEN_SVG, svg_to_icon


def _to_halfwidth(text: str) -> str:
    """把常见全角字符纠正为半角，与登录窗的规整规则保持一致。"""
    result: list[str] = []
    for ch in text:
        code = ord(ch)
        if code == 0x3000:
            result.append(" ")
        elif 0xFF01 <= code <= 0xFF5E:
            result.append(chr(code - 0xFEE0))
        else:
            result.append(ch)
    return "".join(result)


class RekeyWorker(QThread):
    """后台执行「保险备份 + 原地换密」的 QThread。

    换密通过 :meth:`SmData.rekey` 进行，该方法在成功同时会把
    ``SmData._password`` 更新为新密码，保证后续 ``save()`` 会
    用新密码重新加密。文件 I/O 与 Argon2id 派生均在线程内完成，
    避免阻塞 UI。
    """

    # 阶段文字（供 QProgressDialog.setLabelText）
    stage = pyqtSignal(str)
    # finished(success, backup_path_or_none, error_message)
    done = pyqtSignal(bool, object, str)

    def __init__(
        self,
        sm_data: SmData,
        new_password: str,
        backup_dir: Path,
        config_file_path: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._sm_data = sm_data
        self._new_password = new_password
        self._backup_dir = backup_dir
        self._config_file_path = config_file_path

    def run(self) -> None:  # pragma: no cover - UI 线程行为
        backup_path: Path | None = None
        # 1) 保险备份
        self.stage.emit(RekeyText.STAGE_BACKUP)
        try:
            svc = BackupService(self._backup_dir)
            backup_path = svc.create(
                self._sm_data.file_path,
                prefix="rekey",
                config_file=self._config_file_path,
            )
        except StorageError as e:
            logger.error(f"rekey 保险备份失败: {e}")
            self.done.emit(False, None, f"{RekeyText.FAIL_BACKUP}{e}")
            return
        except Exception as e:  # noqa: BLE001
            logger.exception("rekey 保险备份异常")
            self.done.emit(False, None, f"{RekeyText.FAIL_BACKUP}{e}")
            return

        # 2) 原地换密（成功后 SmData._password 已更新为 new_password）
        self.stage.emit(RekeyText.STAGE_REKEY)
        try:
            self._sm_data.rekey(self._new_password)
        except (CryptoError, StorageError, ValueError) as e:
            logger.error(f"rekey 重新加密失败: {e}")
            self.done.emit(False, backup_path, f"{RekeyText.FAIL_REKEY}{e}")
            return
        except Exception as e:  # noqa: BLE001
            logger.exception("rekey 重新加密异常")
            self.done.emit(False, backup_path, f"{RekeyText.FAIL_REKEY}{e}")
            return

        self.done.emit(True, backup_path, "")


class RekeyDialog(Dialog):
    """「更换主密码」对话框。

    Args:
        info: 当前已解锁会话。对话框仅读取其中的 ``account`` 与 ``hashpw``；
            成功时通过 ``finished_ok`` 信号回传新密码，由设置页负责更新
            会话、saved_files、AppConfig 加密密钥等外部状态。
    """

    # finished_ok(new_password: str, backup_path: str)
    finished_ok = pyqtSignal(str, str)

    def __init__(self, info: ZhmmFileInfo, parent: QWidget | None = None) -> None:
        super().__init__()
        self._info = info
        self._worker: RekeyWorker | None = None
        self._progress: QProgressDialog | None = None
        if parent is not None:
            self.setParent(parent, Qt.WindowType.Dialog)

        self.setWindowTitle(RekeyText.TITLE)
        self.setFixedSize(440, 320)
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Dialog)
        self.setModal(True)

        self._icon_eye_open = svg_to_icon(EYE_OPEN_SVG)
        self._icon_eye_closed = svg_to_icon(EYE_CLOSED_SVG)

        self._build_ui()

    # ------------------------------------------------------------------
    # UI 构建
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        title = QLabel(RekeyText.TITLE)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        layout.addWidget(title)

        hint = QLabel(RekeyText.HINT)
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #666; font-size: 12px;")
        layout.addWidget(hint)

        layout.addSpacing(8)

        form = QGridLayout()
        form.setHorizontalSpacing(8)
        form.setVerticalSpacing(10)

        self.old_input = self._make_password_input()
        self.new_input = self._make_password_input()
        self.confirm_input = self._make_password_input()

        rows = (
            (RekeyText.LABEL_OLD, self.old_input),
            (RekeyText.LABEL_NEW, self.new_input),
            (RekeyText.LABEL_CONFIRM, self.confirm_input),
        )
        for row, (label_text, line_row) in enumerate(rows):
            form.addWidget(QLabel(label_text), row, 0)
            form.addLayout(line_row, row, 1)

        layout.addLayout(form)
        layout.addSpacing(12)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        ok_btn = QPushButton(RekeyText.BTN_OK)
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(self._on_confirm)
        btn_row.addWidget(ok_btn)
        cancel_btn = QPushButton(RekeyText.BTN_CANCEL)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)

    def _make_password_input(self) -> QHBoxLayout:
        """返回一行「QLineEdit + 眼睛切换」布局，已绑定全角规整。"""
        line_edit = QLineEdit()
        line_edit.setEchoMode(QLineEdit.EchoMode.Password)
        line_edit.textEdited.connect(lambda _t, le=line_edit: self._normalize(le))

        toggle_btn = QPushButton()
        toggle_btn.setIcon(self._icon_eye_closed)
        toggle_btn.setIconSize(QSize(18, 18))
        toggle_btn.setCheckable(True)
        toggle_btn.setFixedWidth(36)
        toggle_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        toggle_btn.toggled.connect(lambda checked, le=line_edit, btn=toggle_btn: self._toggle_echo(le, btn, checked))

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(line_edit)
        row.addWidget(toggle_btn)

        # 把 line_edit 挂到 row 上，便于后续取值；QLineEdit 作为"逻辑输入"引用。
        row.line_edit = line_edit  # type: ignore[attr-defined]
        return row

    @staticmethod
    def _normalize(line_edit: QLineEdit) -> None:
        original = line_edit.text()
        normalized = _to_halfwidth(original)
        if normalized == original:
            return
        pos = line_edit.cursorPosition()
        line_edit.blockSignals(True)
        try:
            line_edit.setText(normalized)
            line_edit.setCursorPosition(min(pos, len(normalized)))
        finally:
            line_edit.blockSignals(False)

    def _toggle_echo(self, line_edit: QLineEdit, btn: QPushButton, checked: bool) -> None:
        if checked:
            line_edit.setEchoMode(QLineEdit.EchoMode.Normal)
            btn.setIcon(self._icon_eye_open)
        else:
            line_edit.setEchoMode(QLineEdit.EchoMode.Password)
            btn.setIcon(self._icon_eye_closed)

    def showEvent(self, event: QShowEvent):  # type: ignore[override]
        super().showEvent(event)
        enabled = True
        if zhmm.setting is not None:
            enabled = zhmm.setting.get_anti_screenshot()
        apply_anti_capture(self, enabled=enabled)

    # ------------------------------------------------------------------
    # 校验与提交
    # ------------------------------------------------------------------
    def _get_password(self, row: QHBoxLayout) -> str:
        le: QLineEdit = row.line_edit  # type: ignore[attr-defined]
        return _to_halfwidth(le.text()).strip()

    def _on_confirm(self) -> None:
        old_pw = self._get_password(self.old_input)
        new_pw = self._get_password(self.new_input)
        confirm_pw = self._get_password(self.confirm_input)

        if not old_pw:
            self._warn(RekeyText.ERR_OLD_EMPTY)
            return
        if not new_pw:
            self._warn(RekeyText.ERR_NEW_EMPTY)
            return
        if new_pw != confirm_pw:
            self._warn(RekeyText.ERR_CONFIRM_MISMATCH)
            return
        if new_pw == old_pw:
            self._warn(RekeyText.ERR_SAME_AS_OLD)
            return

        hashpw = self._info.get("hashpw") or ""
        try:
            if not hashpw or not bcrypt.checkpw(old_pw.encode(), hashpw.encode()):
                self._warn(RekeyText.ERR_OLD_WRONG)
                return
        except ValueError:
            self._warn(RekeyText.ERR_OLD_WRONG)
            return

        self._start_worker(old_pw, new_pw)

    def _warn(self, msg: str) -> None:
        QMessageBox.warning(self, RekeyText.TITLE, msg)

    # ------------------------------------------------------------------
    # 后台执行与进度反馈
    # ------------------------------------------------------------------
    def _start_worker(self, old_pw: str, new_pw: str) -> None:
        file_path = self._info.get("file_path") or ""
        account = self._info.get("account") or ""
        sm_data = self._info.get("sm_data")
        if not file_path or not account or sm_data is None:
            self._warn(f"{RekeyText.FAIL_TITLE}：会话信息缺失")
            return

        backup_dir = file_util.get_full_path(".backups")
        data_file_name = Path(file_path).stem
        config_file_path = str(file_util.get_full_path(data_file_name))

        progress = QProgressDialog(RekeyText.STAGE_BACKUP, "", 0, 0, self)
        progress.setWindowTitle(RekeyText.PROGRESS_TITLE)
        progress.setWindowModality(Qt.WindowModality.ApplicationModal)
        progress.setCancelButton(None)  # 不可取消
        progress.setMinimumDuration(0)
        progress.setAutoClose(False)
        progress.setAutoReset(False)
        self._progress = progress

        worker = RekeyWorker(
            sm_data=sm_data,
            new_password=new_pw,
            backup_dir=backup_dir,
            config_file_path=config_file_path,
            parent=self,
        )
        worker.stage.connect(progress.setLabelText)
        worker.done.connect(lambda ok, bkp, err, p=progress, np=new_pw: self._on_worker_done(ok, bkp, err, p, np))
        self._worker = worker

        progress.show()
        worker.start()

    def _on_worker_done(
        self,
        ok: bool,
        backup_path: object,
        error: str,
        progress: QProgressDialog,
        new_password: str,
    ) -> None:
        progress.close()
        self._progress = None
        if self._worker is not None:
            self._worker.wait()
            self._worker.deleteLater()
            self._worker = None

        if not ok:
            QMessageBox.critical(self, RekeyText.FAIL_TITLE, error or RekeyText.FAIL_TITLE)
            return

        bkp_str = str(backup_path) if backup_path is not None else ""
        self.finished_ok.emit(new_password, bkp_str)
        self.accept()
