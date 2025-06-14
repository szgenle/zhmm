import json

from zhmm.utils import file_util
from zhmm import sm_util, sm_data
from zhmm.utils import data_conversion
from zhmm.utils.log import logger

class UIDecryptData:

    def __init__(self) -> None:
        pass

    def decrypt_file(self, file_path: str, openid: str, password: str):
        """显示登录对话框"""
        content = file_util.get_file_content(file_path)
        if content is None:
            content = ''
        return self.decrypt(content, openid, password)
        

    def decrypt(self, content: str, openid: str, password: str) -> str:
        # 验证逻辑，使用现有的gl_data验证方法
        try:
            # 处理密码，与cmd_ui.py中相同的逻辑
            pwd_suffix = password + 'woie*#jk20kH2^D@U28)'
            pwd = sm_util.hash_by_sm3(data_conversion.chars_to_bytes(pwd_suffix))

            smdata = sm_data.SmData()
            smdata.init(openid, pwd)

            if content == '':
                user_mm_data = {
                    'userID': openid,
                    'pwd': password,
                    'url': 'szgenle',
                    'desc': '务必记住当前的userID和密码'
                }
                smdata.add_with_dict(user_mm_data)
            else:
                decrypt_result = smdata.decrypt(content)

                if not decrypt_result or not decrypt_result['res']:
                    logger.error(f"解密失败")
                    return

                user_mm_data = json.loads(decrypt_result['res'])
                smdata.set_mm(user_mm_data)
            return smdata

        except Exception as e:
            logger.error(f"解密失败出错: {str(e)}")
            
