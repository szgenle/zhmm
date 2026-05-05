#!/usr/bin/env python3
"""命令行交互 UI。"""

from __future__ import annotations

import argparse
import os.path
import sys
import time

from zhmm.core import totp as totp_mod
from zhmm.core.errors import ValidationError
from zhmm.core.export_service import ExportService
from zhmm.core.models import PasswordEntry
from zhmm.data.sm_data_manager import SmData
from zhmm.data.sm_data_types import ZhmmDict
from zhmm.utils import date_util
from zhmm.utils.table_printer import TablePrinter


def _normalize_search_word(word: str) -> str:
    """去除首尾空白及成对的引号（容错不同 shell 未剥离引号的场景）。"""
    w = word.strip()
    # 反复剥离首尾成对的单/双引号，兼容 '"abc"' / "'abc'" 等被转义后传入的情形
    while len(w) >= 2 and w[0] == w[-1] and w[0] in ('"', "'"):
        w = w[1:-1].strip()
    return w


class CmdUI:
    sm_data: SmData = SmData()
    fixed_id_is_None: bool = False

    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args

    # ------------------------------------------------------------------
    # 查询
    # ------------------------------------------------------------------
    def user_find(self) -> None:
        print("您好，请输入您想查找的信息(可用空格间隔多个关键字，按ESC退出)")
        info = input("请输入:").strip()
        if info == "\x1b":
            print("\n再见\n")
            sys.exit(0)
        self.user_search(info)

    def user_search(self, search_word: str) -> None:
        if not search_word:
            print("搜索关键字不能为空")
            return
        infos: list[ZhmmDict] | None = self.sm_data.search(search_word)
        if infos:
            print(f"您好，查找到[{search_word}]的相关信息：")
            TablePrinter.print_info([dict(info) for info in infos], SmData.keys, SmData.heads)
        else:
            print(f"您好，没有查找到[{search_word}]的相关信息：")

    # ------------------------------------------------------------------
    # 新增
    # ------------------------------------------------------------------
    def user_new(self) -> None:
        print("您好，请输入您要添加的账号密码" "(输入用空格间隔的一组会自动分成['账号', '密码', '网站', '备注'])")
        en_names = ["userID", "pwd", "url", "desc"]
        cn_names = [SmData.field_mapping[field] for field in en_names]

        en_infos, cn_infos = self.collect_account_info(en_names, cn_names)
        self.confirm_and_save(en_infos, cn_infos)

    def collect_account_info(self, en_names: list[str], cn_names: list[str]) -> tuple[dict[str, str], dict[str, str]]:
        en_infos: dict[str, str] = {}
        cn_infos: dict[str, str] = {}
        for i in range(4):
            info = input(f"请输入{cn_names[i]}:").strip()
            if info == "\x1b":
                print("\n取消操作\n")
                return {}, {}
            if " " in info:
                self.process_multi_value_input(i, info, en_names, cn_names, en_infos, cn_infos)
                break
            en_infos[en_names[i]] = info
            cn_infos[cn_names[i]] = info
        return en_infos, cn_infos

    def process_multi_value_input(
        self,
        start_idx: int,
        input_str: str,
        en_names: list[str],
        cn_names: list[str],
        en_infos: dict[str, str],
        cn_infos: dict[str, str],
    ) -> None:
        infos = input_str.split()
        for j in range(min(4 - start_idx, len(infos))):
            idx = start_idx + j
            en_infos[en_names[idx]] = infos[j]
            cn_infos[cn_names[idx]] = infos[j]

    def build_zhmm_dict(self, en_infos: dict[str, str]) -> ZhmmDict:
        return {
            "id": date_util.timestamp_int(),
            "role": "个人",
            "userID": en_infos.get("userID", ""),
            "pwd": en_infos.get("pwd", ""),
            "phone": None,
            "email": None,
            "url": en_infos.get("url", ""),
            "desc": en_infos.get("desc", ""),
            "utime": date_util.timestamp_int(),
            "tags": None,
            "history": None,
        }

    def confirm_and_save(self, en_infos: dict[str, str], cn_infos: dict[str, str]) -> None:
        if not en_infos or not cn_infos:
            return
        print("新增账号信息：", cn_infos)
        confirm = input("确认增加[y/n]？: ").strip().upper()
        if confirm == "\x1b":
            print("\n取消操作\n")
            return
        if confirm == "Y":
            dict_info: ZhmmDict = self.build_zhmm_dict(en_infos)
            self.sm_data.add(dict_info)
            self.save()

    # ------------------------------------------------------------------
    # 主流程
    # ------------------------------------------------------------------
    def save(self) -> None:
        file_path = self.args.out if self.args.out else self.args.input
        if self.sm_data.save(file_path):
            print("操作成功!")

    def user_option(self) -> int:
        time.sleep(0.3)
        op = input("新增[n/N]查找[f/F]导出[e/E]删除[d/D]退出[q/Q/ESC]:").strip().lower()
        if op == "\x1b" or op is None or op == "q":
            return -1
        if op == "n":
            self.args.new = True
        elif op == "f":
            self.args.find = True
        elif op == "e":
            self.args.export = True
        elif op == "d":
            self.args.delete = True
        return 0

    def run(self, file_path: str, account: str, password: str) -> None:
        """加载文件并进入交互循环。"""
        self.sm_data.init(account, password)
        if not self.sm_data.load(file_path):
            print("账号文件打开失败或账号/密码不对")
            return
        self.fix_id_is_None()
        # --totp 快通道：打印验证码后直接退出，不进交互循环
        if getattr(self.args, "totp", None) is not None:
            self.user_totp(int(self.args.totp))
            return
        try:
            self.user_input_ui()
        except KeyboardInterrupt:
            print("\n再见\n")
        finally:
            print("\n再见\n")

    def user_input_ui(self) -> None:
        while True:
            if self.args.search:
                search_word = _normalize_search_word(self.args.search)
                self.args.search = None
                self.user_search(search_word)
                if self.args.once:
                    break
                if self.args.simple:
                    continue
            elif self.args.simple:
                self.user_find()
                continue
            elif self.args.find:
                self.args.find = False
                self.user_find()
            elif self.args.new:
                self.args.new = False
                self.user_new()
            elif self.args.export:
                self.args.export = False
                self.user_export()
            elif self.args.delete:
                self.args.delete = False
                self.user_delete()

            if self.user_option() < 0:
                print("\n再见\n")
                break

    def user_export(self) -> None:
        file_path = input("请输入导出的路径:").strip()
        if file_path == "\x1b":
            print("\n取消操作\n")
            return
        if file_path and os.path.exists(file_path):
            file_path = os.path.join(file_path, "zhmm.xlsx")
            entries = [PasswordEntry.from_dict(dict(item)) for item in self.sm_data.mm["data"]]
            try:
                ExportService.export_xlsx(file_path, entries)
                print(f"已导出到 {file_path}")
            except Exception as e:
                print(f"导出失败: {e}")

    def user_delete(self) -> None:
        try:
            ids = input("请输入要删除的ID(多个ID用空格隔开):").strip()
            if ids == "\x1b":
                print("\n取消操作\n")
                return
            id_list = [int(id_str) for id_str in ids.split()]
            deled = False
            for zh_id in id_list:
                if isinstance(zh_id, int) and zh_id > 0:
                    self.sm_data.delete(zh_id)
                    deled = True
                else:
                    print(f"忽略无效ID: {zh_id}")
            if deled:
                self.save()
        except ValueError:
            print("错误：请输入有效的数字ID（多个ID用空格分隔）")

    def fix_id_is_None(self) -> None:
        if not self.sm_data.fix_id_is_None():
            self.fixed_id_is_None = True
            import threading

            timer = threading.Timer(1.0, self.fix_id_is_None)
            timer.daemon = True
            timer.start()
        elif self.fixed_id_is_None:
            self.save()

    # ------------------------------------------------------------------
    # TOTP 快通道
    # ------------------------------------------------------------------
    def user_totp(self, rid: int) -> None:
        """打印指定 ID 条目的当前 TOTP 验证码与剩余秒数。

        条目不存在或未启用 TOTP 时给中性提示，不会泄露敏感信息。
        """
        if not self.sm_data.mm or not self.sm_data.mm.get("data"):
            print("密码库为空")
            return
        for item in self.sm_data.mm["data"]:
            if item.get("id") != rid:
                continue
            secret = str(item.get("totp_secret") or "").strip()
            if not secret:
                print(f"条目 {rid} 未启用 TOTP")
                return
            algo = str(item.get("totp_algo") or totp_mod.DEFAULT_ALGO).upper()
            try:
                digits_raw = item.get("totp_digits") or totp_mod.DEFAULT_DIGITS
                period_raw = item.get("totp_period") or totp_mod.DEFAULT_PERIOD
                digits = int(digits_raw)  # type: ignore[call-overload]
                period = int(period_raw)  # type: ignore[call-overload]
                code = totp_mod.generate(secret, algo=algo, digits=digits, period=period)
                left = totp_mod.remaining_seconds(period)
            except (ValidationError, TypeError, ValueError) as ex:
                print(f"TOTP 计算失败: {ex}")
                return
            print(f"{code}  (剩余 {left}s, algo={algo})")
            return
        print(f"找不到条目 ID={rid}")


__all__ = ["CmdUI"]
