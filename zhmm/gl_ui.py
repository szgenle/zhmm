#!/usr/bin/env python3
# coding=utf-8
# @Author: Lioesquieu
# @Date: 2024-06-30
# @LastEditTime: 2024-07-02
import time
import json
import gl_sm_util

import gl_util
from gl_data import GlData
from zhmm.utils import file_sys

gl_data = GlData()


def print_list(data):
    # print(data)
    # 获取列的最大宽度（可选，用于对齐）
    def str_len(item):
        cnt = gl_util.count_unicode_chars(item)
        if cnt == 0:
            return len(str(item))
        else:
            return len(str(item)) + cnt

    max_widths = [max(str_len(item) for item in col) for col in zip(*data)]
    # print(max_widths)

    def item_width(item, width):
        cnt = gl_util.count_unicode_chars(item)
        if cnt > 0:
            dc = width - len(item)
            if dc > cnt:
                dc = cnt
            if dc > 0:
                width = width - dc
        return width

    # 打印表头
    for item, width in zip(data[0], max_widths):
        width = item_width(item, width)
        print(f"{item:^{width}}", end='|')
    print()  # 换行

    # 打印表格内容
    for row in data[1:]:
        for item, width in zip(row, max_widths):
            width = item_width(item, width)
            print(f"{item:<{width}}", end='|')
        print()  # 每行结束后换行


def print_info(infos):
    arrs = []
    cn_heads = ['类别', '账号', '密码', '手机', '邮箱', '网站', '备注']
    en_heads = ['role', 'userID', 'pwd', 'phone', 'email', 'url', 'desc']
    arrs.append(cn_heads)
    for info in infos:
        values = []
        for key in en_heads:
            if key not in info:
                values.append('')
            elif not gl_util.is_string(info[key]):
                values.append(str(info[key]))
            else:
                values.append(info[key])
        arrs.append(values)
        # arrs.append([item for item in original_list if item and item != ""])
        # print([item for item in original_list if item and item != ""])
    # print(arrs)
    print_list(arrs)
    pass


class ClUI:

    args = {}

    def __init__(self, args):
        self.args = args
        pass

    def user_find(self):
        print("您好，请输入您想查找的信息(可用空格间隔多个关键字)")
        info = input("请输入:").strip()
        self.user_search(info)

    def user_search(self, search_word):
        finds = gl_data.search(search_word)
        if finds and len(finds) > 0:
            print("您好，查找到[%s]的相关信息：" % search_word)
            print_info(finds)
        else:
            print("您好，没有查找到[%s]的相关信息：" % search_word)

    def user_new(self):
        print("您好，请输入您要添加的账号密码(输入用空格间隔的一组会自动分成['账号', '密码', '网站', '备注'])")
        cn_names = ['账号', '密码', '网站', '备注']
        en_names = ['userID', 'pwd', 'url', 'desc']
        en_infos = {}
        cn_infos = {}
        for i in range(4):
            info = input("请输入%s:" % (cn_names[i])).strip()
            infos = info.split()
            infos_len = len(infos)
            if infos_len > 1:
                for j in range(min(4-i, infos_len)):
                    cn_infos[cn_names[i+j]] = infos[j]
                    en_infos[en_names[i+j]] = infos[j]
                break
            cn_infos[cn_names[i]] = info
            en_infos[en_names[i]] = info
        print("新增账号信息：", cn_infos)
        ok = input("确认增加[y/n]？: ").strip()
        if ok == 'y' or ok == 'Y':
            file_path = self.args.input
            if self.args.out:
                file_path = self.args.out
            if gl_data.add(en_infos, file_path):
                print("添加成功!")

    def user_option(self):
        time.sleep(0.3)
        op = input("新增[n/N]查找[f/F]退出[q/Q]:").strip().lower()
        if op == 'q':
            print('再见')
            exit(0)
        elif op == 'n':
            self.args.new = True
        elif op == 'f':
            self.args.find = True
        return 0

    def run(self, file_path, open_id, password):

        pwd_suffix = password + 'woie*#jk20kH2^D@U28)'
        pwd = gl_sm_util.hash_by_sm3(gl_util.string_to_hex_array(pwd_suffix))
        gl_data.init(open_id, pwd)

        data = file_sys.get_file_content(file_path)
        if data:
            decrypt_result = gl_data.decrypt(data)

            if not decrypt_result or not decrypt_result['res']:
                print("密码不对")
                return False

            user_mm_data = json.loads(decrypt_result['res'])
            gl_data.set_mm(user_mm_data)

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
            if self.user_option() < 0:
                break

