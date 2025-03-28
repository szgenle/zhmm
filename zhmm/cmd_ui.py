#!/usr/bin/env python3
# coding=utf-8
# @Author: Lioesquieu
# @Date: 2024-06-30
# @LastEditTime: 2024-07-02
import time
import json
import sm_util
from zhmm.data_exporter import DataExporter

from zhmm.sm_data import SmData, ZhmmDict
from zhmm.utils import file_util, data_conversion
from zhmm.utils.table_printer import TablePrinter

gl_data1 = SmData()


def print_info(infos):
    
    # 使用field_mapping重构字段映射
    required_fields = ['role', 'userID', 'pwd', 'phone', 'email', 'url', 'desc']
    cn_headers = [SmData.field_mapping[field] for field in required_fields]

    arrs = []
    arrs.append(cn_headers)
    
    for info in infos:
        values = []
        for field in required_fields:
            # 统一使用字段映射获取值
            value = info.get(field, '')
            if not isinstance(value, str):
                value = str(value)
            values.append(value)
        arrs.append(values)

    TablePrinter.print_list(arrs)
    pass


class CmdUI:

    def __init__(self, args):
        self.args = args
        pass

    def user_find(self):
        print("您好，请输入您想查找的信息(可用空格间隔多个关键字)")
        info = input("请输入:").strip()
        self.user_search(info)

    def user_search(self, search_word):
        finds = gl_data1.search(search_word)
        if finds and len(finds) > 0:
            print("您好，查找到[%s]的相关信息：" % search_word)
            print_info(finds)
        else:
            print("您好，没有查找到[%s]的相关信息：" % search_word)

    def user_new(self):
        print("您好，请输入您要添加的账号密码(输入用空格间隔的一组会自动分成['账号', '密码', '网站', '备注'])")
        cn_names = ['账号', '密码', '网站', '备注']
        en_names = ['userID', 'pwd', 'url', 'desc']
        en_infos: dict = {}  # 使用普通dict初始化
        cn_infos = {}
        for i in range(4):
            info = input("请输入%s:" % (cn_names[i])).strip()
            infos = info.split()
            infos_len = len(infos)
            if infos_len > 1:
                for j in range(min(4 - i, infos_len)):
                    cn_infos[cn_names[i + j]] = infos[j]
                    en_infos[en_names[i + j]] = infos[j]
                break
            cn_infos[cn_names[i]] = info
            en_infos[en_names[i]] = info
        print("新增账号信息：", cn_infos)
        ok = input("确认增加[y/n]？: ").strip()
        if ok == 'y' or ok == 'Y':
            file_path = self.args.input
            if self.args.out:
                file_path = self.args.out
            # 将普通dict转换为ZhmmDict类型
            dict_info: ZhmmDict = {
                'id': None,
                'role': '个人',
                'userID': en_infos.get('userID', ''),
                'pwd': en_infos.get('pwd', ''),
                'phone': None,
                'email': None,
                'url': en_infos.get('url', ''),
                'desc': en_infos.get('desc', ''),
                'utime': None
            }
            if gl_data1.add(dict_info, file_path):
                print("添加成功!")

    def user_option(self):
        time.sleep(0.3)
        try:
            op = input("新增[n/N]查找[f/F]导出[e/E]退出[q/Q]:").strip().lower()
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
        return 0

    def run(self, file_path, open_id, password):

        pwd_suffix = password + 'woie*#jk20kH2^D@U28)'
        pwd = sm_util.hash_by_sm3(data_conversion.chars_to_bytes(pwd_suffix))
        gl_data1.init(open_id, pwd)

        data = file_util.get_file_content(file_path)
        if data:
            decrypt_result = gl_data1.decrypt(data)

            if not decrypt_result or not decrypt_result['res']:
                print("密码不对")
                return False
            user_mm_data = json.loads(decrypt_result['res'])
            gl_data1.set_mm(user_mm_data)

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
                DataExporter.export_to_file(gl_data1.mm['data'])
            if self.user_option() < 0:
                break
