import os
import time
import hmac
import hashlib
import base64
import requests
from pathlib import Path
from urllib.parse import quote, urlencode
from datetime import datetime
from qcloud_cos import CosConfig, CosS3Client
import sys
import logging
from src.config import (
    TENCENT_SECRET_ID, 
    TENCENT_SECRET_KEY, 
    TENCENT_APPID, 
    COS_REGION, 
    COS_BUCKET
)

from src.config import config # Add this import statement

class COSUploader:
    def __init__(self):
        self.secret_id = TENCENT_SECRET_ID
        self.secret_key = TENCENT_SECRET_KEY
        self.region = COS_REGION
        self.appid = TENCENT_APPID
        # 存储桶名称格式：bucketname-appid
        self.bucket = f"{COS_BUCKET}-{self.appid}"
        
        # 创建COS客户端，按照官方文档配置
        cos_config = CosConfig(
            Region=self.region,
            SecretId=self.secret_id,
            SecretKey=self.secret_key
        )
        self.client = CosS3Client(cos_config)
        
        # 创建缓存目录
        self.temp_dir = config.CACHE_DIR / "cos"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        # 配置日志
        logging.basicConfig(level=logging.INFO, stream=sys.stdout)
        
    def _get_sign_key(self, key, msg):
        """计算签名密钥"""
        return hmac.new(key.encode('utf-8'), msg.encode('utf-8'), hashlib.sha1)
        
    def _get_authorization(self, http_method, path):
        """生成授权签名"""
        q_sign_algorithm = 'sha1'
        q_ak = self.secret_id
        q_sign_time = f"{int(time.time())};{int(time.time()) + 3600}"  # 1小时有效期
        q_key_time = q_sign_time
        q_header_list = ''
        q_url_param_list = ''
        
        # 1. 生成 SignKey
        sign_key = hmac.new(
            self.secret_key.encode('utf-8'),
            q_key_time.encode('utf-8'),
            hashlib.sha1
        ).hexdigest()
        
        # 2. 生成 UrlParamList 和 HttpParameters
        url_param_list = []
        http_parameters = ''
        
        # 3. 生成 HeaderList 和 HttpHeaders
        header_list = []
        http_headers = f'host={self.bucket}.cos.{self.region}.myqcloud.com\n'
        
        # 4. 生成 HttpString
        http_string = (
            f'{http_method.lower()}\n{path}\n{http_parameters}\n'
            f'{http_headers}\n'
        )
        
        # 5. 生成 StringToSign
        string_to_sign = (
            f'{q_sign_algorithm}\n{q_sign_time}\n'
            f'{hashlib.sha1(http_string.encode("utf-8")).hexdigest()}\n'
        )
        
        # 6. 生成 Signature
        signature = hmac.new(
            sign_key.encode('utf-8'),
            string_to_sign.encode('utf-8'),
            hashlib.sha1
        ).hexdigest()
        
        # 7. 生成 Authorization
        authorization = (
            f'q-sign-algorithm={q_sign_algorithm}&'
            f'q-ak={q_ak}&'
            f'q-sign-time={q_sign_time}&'
            f'q-key-time={q_key_time}&'
            f'q-header-list={q_header_list}&'
            f'q-url-param-list={q_url_param_list}&'
            f'q-signature={signature}'
        )
        
        return authorization
        
    def _download_file(self, url, local_path):
        """下载远程文件到本地"""
        try:
            print(f"正在下载远程文件: {url}")
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            block_size = 8192
            
            with open(local_path, 'wb') as f:
                if total_size == 0:
                    f.write(response.content)
                else:
                    downloaded = 0
                    for data in response.iter_content(block_size):
                        downloaded += len(data)
                        f.write(data)
                        done = int(50 * downloaded / total_size)
                        print(f"\r下载进度: [{'=' * done}{' ' * (50-done)}] {downloaded}/{total_size} bytes", end='')
            print("\n下载完成！")
            return True
        except Exception as e:
            print(f"下载文件失败: {str(e)}")
            return False

    def upload(self, file_path: str) -> str:
        """上传文件到COS
        
        Args:
            file_path: 本地文件路径
            
        Returns:
            str: 文件的COS URL
        """
        try:
            print(f"正在上传文件到COS: {file_path}")
            print(f"存储桶: {self.bucket}")
            print(f"地区: {self.region}")
            
            # 生成COS中的文件key
            file_key = f"audio/{int(time.time())}_{Path(file_path).name}"
            
            # 上传文件
            with open(file_path, 'rb') as f:
                response = self.client.put_object(
                    Bucket=self.bucket,
                    Body=f,
                    Key=file_key
                )
            
            # 返回文件URL
            url = f'https://{self.bucket}.cos.{self.region}.myqcloud.com/{file_key}'
            print(f"文件已上传，URL: {url}")
            return url
            
        except Exception as e:
            print(f"上传文件失败: {str(e)}")
            if hasattr(e, 'get_error_info'):
                error_info = e.get_error_info()
                print(f"错误详情: {error_info}")
            raise Exception(f"上传文件失败: {str(e)}")

    def delete(self, file_url):
        """从COS删除文件"""
        try:
            # 从URL提取key
            key = file_url.split(f"{self.bucket}.cos.{self.region}.myqcloud.com/")[1]
            
            # 删除文件
            self.client.delete_object(
                Bucket=self.bucket,
                Key=key
            )
            print(f"已从COS删除文件: {key}")
            return True
            
        except Exception as e:
            print(f"删除文件失败: {str(e)}")
            return False