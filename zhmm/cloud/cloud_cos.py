import json
import os
from pathlib import Path

from qcloud_cos import CosConfig, CosS3Client

from zhmm.cloud.cloud_base import CloudBase


class CloudCos(CloudBase):

    client: CosS3Client = None
    bucket: str = None

    def __init__(self):
        pass

    def init(self, config):
        print("初始化COS")

        secret_id = config.get('qcloud.secret_id')
        secret_key = config.get('qcloud.secret_key')
        region = config.get('qcloud.region') # COS 支持的所有 region 列表参见https://cloud.tencent.com/document/product/436/6224
        self.bucket = config.get("qcloud.bucket")

        if not secret_id or not secret_key or not region:
            return False
        token = None               # 如果使用永久密钥不需要填入 token，如果使用临时密钥需要填入，临时密钥生成和使用指引参见 https://cloud.tencent.com/document/product/436/14048
        scheme = 'https'           # 指定使用 http/https 协议来访问 COS，默认为 https，可不填

        cos_config = CosConfig(Region=region, SecretId=secret_id, SecretKey=secret_key, Token=token, Scheme=scheme)
        self.client = CosS3Client(cos_config)
        return True

    
    def sync_data(self):
        print('sync_data', path)
        pass

    def get_full_path(self, path: str) -> Path:
        print('get_full_path', path)
        pass

    def get_file_content(self, path):
        ####  获取文件到本地
        try:
            response = self.client.get_object(
                Bucket=self.bucket,
                Key=path
            )
            fp = response['Body'].get_raw_stream()
            content = fp.read()
            fp.close()
            return content
        except Exception as e:
            print(e)
            return None

    def set_file_content(self, path, content):
        print('set_file_content', path)
        #### 高级上传接口（推荐）
        # 根据文件大小自动选择简单上传或分块上传，分块上传具备断点续传功能。
        response = self.client.put_object(
            Bucket=self.bucket,
            Body=content,
            Key=path,
            EnableMD5=False
        )
        return response['ETag']

    def rm_file(self, path):
        print('rm_file', path)
        pass
