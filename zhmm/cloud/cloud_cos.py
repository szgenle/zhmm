from pathlib import Path

from qcloud_cos import CosConfig, CosS3Client

from zhmm.cloud.cloud_base import CloudBase
from zhmm.utils.log import logger


class CloudCos(CloudBase):
    client: CosS3Client | None = None
    bucket: str | None = None

    def __init__(self):
        pass

    def init(self, config):
        logger.info("初始化COS客户端")
        secret_id = config.get("qcloud.secret_id")
        secret_key = config.get("qcloud.secret_key")
        region = config.get("qcloud.region")  # COS 支持的所有 region 列表参见https://cloud.tencent.com/document/product/436/6224
        self.bucket = config.get("qcloud.bucket")

        if not secret_id or not secret_key or not region:
            return False
        token = None  # 如果使用永久密钥不需要填入 token，如果使用临时密钥需要填入，临时密钥生成和使用指引参见 https://cloud.tencent.com/document/product/436/14048
        scheme = "https"  # 指定使用 http/https 协议来访问 COS，默认为 https，可不填

        cos_config = CosConfig(
            Region=region,
            SecretId=secret_id,
            SecretKey=secret_key,
            Token=token,
            Scheme=scheme,
        )
        self.client = CosS3Client(cos_config)
        return True

    def sync_data(self):
        logger.debug("COS占位sync_data调用")
        return None

    def get_full_path(self, path: str) -> Path:
        return Path(path)

    def get_file_content(self, path):
        #  获取文件到本地
        if self.client is None:
            logger.error("COS客户端未初始化")
            return None
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=path)
            fp = response["Body"].get_raw_stream()
            content = fp.read()
            fp.close()
            if content:
                return content.decode("utf-8")
        except Exception as e:
            logger.error("COS读取失败: %s", str(e))
            return None

    def set_file_content(self, path, content):
        logger.debug("COS写入文件: %s", path)
        if self.client is None:
            logger.error("COS客户端未初始化")
            return None
        response = self.client.put_object(
            Bucket=self.bucket, Body=content, Key=path, EnableMD5=False
        )
        return response["ETag"]

    def rm_file(self, path):
        logger.debug("COS删除文件: %s", path)
        if self.client is None:
            logger.error("COS客户端未初始化")
            return
        try:
            self.client.delete_object(Bucket=self.bucket, Key=path)
        except Exception as e:
            logger.error("COS删除失败: %s", str(e))
