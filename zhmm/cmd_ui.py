#!/usr/bin/env python3
# coding=utf-8
# @Author: Lioesquieu
# @Date: 2024-06-30
# @LastEditTime: 2024-07-02
import os.path
import time
import json
import sm_util
from zhmm.data_exporter import DataExporter

from zhmm.sm_data import SmData, ZhmmDict
from zhmm.utils import file_util, data_conversion, date_util
from zhmm.utils.table_printer import TablePrinter


class CmdUI:

    sm_data = SmData()
    fixed_id_is_None = False

    def __init__(self, args):
        self.args = args
        pass

    def user_find(self):
        print("您好，请输入您想查找的信息(可用空格间隔多个关键字)")
        info = input("请输入:").strip()
        self.user_search(info)

    def user_search(self, search_word):
        infos: list[ZhmmDict] | None = self.sm_data.search(search_word)
        if infos and len(infos) > 0:
            print("您好，查找到[%s]的相关信息：" % search_word)
            # 将 ZhmmDict 转换为标准字典类型
            TablePrinter.print_info(
                [dict(info) for info in infos],  # 添加类型转换
                SmData.keys,
                SmData.heads
            )
        else:
            print("您好，没有查找到[%s]的相关信息：" % search_word)

    def user_new(self):
        """处理新增账号流程"""
        print("您好，请输入您要添加的账号密码(输入用空格间隔的一组会自动分成['账号', '密码', '网站', '备注'])")
        en_names = ['userID', 'pwd', 'url', 'desc']
        cn_names = [SmData.field_mapping[field] for field in en_names]

        en_infos, cn_infos = self.collect_account_info(en_names, cn_names)
        self.confirm_and_save(en_infos, cn_infos)

    def collect_account_info(self, en_names, cn_names):
        """收集用户输入的账号信息"""
        en_infos = {}
        cn_infos = {}
        
        for i in range(4):
            info = input(f"请输入{cn_names[i]}:").strip()
            if ' ' in info:
                self.process_multi_value_input(i, info, en_names, cn_names, en_infos, cn_infos)
                break
            en_infos[en_names[i]] = info
            cn_infos[cn_names[i]] = info
        return en_infos, cn_infos

    def process_multi_value_input(self, start_idx, input_str, en_names, cn_names, en_infos, cn_infos):
        """处理包含空格的组合输入"""
        infos = input_str.split()
        for j in range(min(4 - start_idx, len(infos))):
            current_idx = start_idx + j
            en_infos[en_names[current_idx]] = infos[j]
            cn_infos[cn_names[current_idx]] = infos[j]

    def build_zhmm_dict(self, en_infos) -> ZhmmDict:
        """构建要存储的字典对象"""
        return {
            'id': date_util.timestamp_int(),
            'role': '个人',
            'userID': en_infos.get('userID', ''),
            'pwd': en_infos.get('pwd', ''),
            'phone': None,
            'email': None,
            'url': en_infos.get('url', ''),
            'desc': en_infos.get('desc', ''),
            'utime': date_util.timestamp_int()
        }

    def confirm_and_save(self, en_infos, cn_infos):
        """确认并保存账号信息"""
        print("新增账号信息：", cn_infos)
        if input("确认增加[y/n]？: ").strip().upper() == 'Y':
            dict_info: ZhmmDict = self.build_zhmm_dict(en_infos)
            self.sm_data.add(dict_info)
            self.save()

    def save(self):
        """保存数据到文件"""
        file_path = self.args.out if self.args.out else self.args.input
        if self.sm_data.save(file_path):
            print("添加成功!")

    def user_option(self):
        time.sleep(0.3)
        try:
            op = input("新增[n/N]查找[f/F]导出[e/E]删除[d/D]退出[q/Q]:").strip().lower()
        except KeyboardInterrupt:
            print('再见')
            exit(0)

        if op == 'q':
            print('再见')
            exit(0)
        elif op == 'n':
            self.args.new = True
        elif op == 'f':
            self.args.find = True
        elif op == 'e':
            self.args.export = True
        elif op == 'd':
            self.args.delete = True
        return 0

    def get_decrypt_data(self, file_path, open_id, password):
        pwd_suffix = password + 'woie*#jk20kH2^D@U28)'
        pwd = sm_util.hash_by_sm3(data_conversion.chars_to_bytes(pwd_suffix))
        self.sm_data.init(open_id, pwd)

        data = file_util.get_file_content(file_path)
        if not data:
            print("密码文件打开失败")
            return

        decrypt_result = self.sm_data.decrypt(data)

        if not decrypt_result or not decrypt_result['res']:
            print("密码不对")
            return
        return decrypt_result

    def run(self, file_path, open_id, password):
        decrypt_result = self.get_decrypt_data(file_path, open_id, password)
        if not decrypt_result:
            return

        user_mm_data = json.loads(decrypt_result['res'])
        self.sm_data.set_mm(user_mm_data)
        self.fix_id_is_None()

        self.user_input_ui()
    
    def user_input_ui(self):
        """响应用户的输入操作"""
        while True:
            if self.args.search:
                self.args.search = None
                self.user_search(self.args.search)
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
                break

    def user_export(self):
        file_path = input("请输入导出的路径:").strip()
        if file_path and os.path.exists(file_path):
            file_path = os.path.join(file_path, 'zhmm.xlsx')
            DataExporter.export_xlsx(file_path, self.sm_data.mm['data'])
    
    def user_delete(self):
        try:
            ids = input("请输入要删除的ID(多个ID用空格隔开):").strip()
            # 分割多个ID并转换为整数
            id_list = [int(id_str) for id_str in ids.split()]
            # 逐个删除
            deled = False
            for zh_id in id_list:
                if isinstance(zh_id, int) and zh_id > 0:
                    self.sm_data.delete(zh_id)
                    deled = True
                else:
                    print(f"忽略无效ID: {zh_id}")
            if deled:
                self.save()  # 所有删除完成后保存一次
        except ValueError:
            print("错误：请输入有效的数字ID（多个ID用空格分隔）")

    def fix_id_is_None(self):
        """
        修复数据中的id字段为None的情况
        """
        if not self.sm_data.fix_id_is_None():
            self.fixed_id_is_None = True
            # 使用threading.Timer替代PyQt的QTimer
            import threading
            timer = threading.Timer(1.0, self.fix_id_is_None)
            timer.daemon = True  # 设置为守护线程防止程序无法退出
            timer.start()
        else:
            if self.fixed_id_is_None:
                self.save()