#!/usr/bin/env python3
# coding=utf-8
# @Author: Lioesquieu
# @Date: 2024-06-30
# @LastEditTime: 2024-07-02
import time
import json
import sm_util
import pandas as pd  # 添加pandas库导入

from zhmm.sm_data import SmData, ZhmmDict
from zhmm.utils import file_util, string_util, data_conversion

gl_data1 = SmData()


def print_list(data):
    # print(data)
    # 获取列的最大宽度（可选，用于对齐）
    def str_len(item):
        cnt = string_util.count_unicode_chars(item)
        if cnt == 0:
            return len(str(item))
        else:
            return len(str(item)) + cnt

    max_widths = [max(str_len(item) for item in col) for col in zip(*data)]

    # print(max_widths)

    def item_width(item, width):
        cnt = string_util.count_unicode_chars(item)
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
            elif not string_util.is_string(info[key]):
                values.append(str(info[key]))
            else:
                values.append(info[key])
        arrs.append(values)
        # arrs.append([item for item in original_list if item and item != ""])
        # print([item for item in original_list if item and item != ""])
    # print(arrs)
    print_list(arrs)
    pass


def export_xlsx(file_path, data):
    """导出xlsx文件"""
    # 准备数据
    cn_heads = ['ID', '类别', '账号', '密码', '手机', '邮箱', '网站', '备注', '更新时间']
    en_heads = ['id', 'role', 'userID', 'pwd', 'phone', 'email', 'url', 'desc', 'utime']

    # 创建一个空的DataFrame
    df = pd.DataFrame(data=None, columns=pd.Index(cn_heads))
    try:

        # 填充数据并清理不兼容的字符
        for item in data:
            row_data = {}
            for i, key in enumerate(en_heads):
                if key in item:
                    # 转换为字符串并清理可能导致Excel问题的字符
                    value = str(item[key])
                    # 替换或移除可能导致Excel问题的字符
                    value = value.replace('\r', '[r]').replace('\n', '[n]')
                    row_data[cn_heads[i]] = value
                else:
                    row_data[cn_heads[i]] = ''
            df = pd.concat([df, pd.DataFrame([row_data])], ignore_index=True)

        # 使用xlsxwriter引擎替代openpyxl
        df.to_excel(file_path, index=False, engine='xlsxwriter')
        print(f"数据已成功导出到: {file_path}")
        return True
    except Exception as e:
        print(f"导出Excel文件失败: {str(e)}")
        # 尝试使用CSV格式作为备选
        try:
            csv_path = file_path.replace('.xlsx', '.csv')
            df.to_csv(csv_path, index=False, encoding='utf-8-sig')
            print(f"已改为CSV格式导出到: {csv_path}")
            return True
        except Exception as csv_e:
            print(f"CSV导出也失败: {str(csv_e)}")
        return False


def export():
    save_file_path = file_util.get_full_path('zhmm.xlsx')
    export_xlsx(save_file_path, gl_data1.mm['data'])
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
            zhmmdict_info: ZhmmDict = {
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
            if gl_data1.add(zhmmdict_info, file_path):
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
        pwd = sm_util.hash_by_sm3(data_conversion.string_to_hex_array(pwd_suffix))
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
                export()
            if self.user_option() < 0:
                break
