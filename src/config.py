# src/config.py
import os
import re
from typing import Literal
from dotenv import load_dotenv
from pathlib import Path

# 加载 .env 文件
load_dotenv()

# 在 load_dotenv() 之后添加
print("正在加载环境变量...")
print(f"SILICON_API_KEY: {'已设置' if os.getenv('SILICON_API_KEY') else '未设置'}")
print(f"TENCENT_SECRET_ID: {'已设置' if os.getenv('TENCENT_SECRET_ID') else '未设置'}")
print(f"TENCENT_SECRET_KEY: {'已设置' if os.getenv('TENCENT_SECRET_KEY') else '未设置'}")

class ConfigError(Exception):
    """自定义配置异常"""
    pass

# ================= 核心配置 =================
_MODEL_MAPPING = {
    # 硅基流动兼容DeepSeek模型标识
    'silicon': {
        'v3': 'Pro/deepseek-ai/DeepSeek-V3',  # 更新为正确的模型名称
        'r1': 'Pro/deepseek-ai/DeepSeek-R1'
    }
}

_API_ENDPOINTS = {
    'silicon': 'https://api.siliconflow.cn/v1/chat/completions'  # 确保URL正确
}

# ============ 密钥验证 ============
def _validate_key(provider: Literal['silicon']):
    """验证API密钥
    
    Args:
        provider: API提供商名称
        
    Returns:
        str: 经过验证的API密钥
        
    Raises:
        ConfigError: 当API密钥未设置或格式不正确时
    """
    key_name = f"{provider.upper()}_API_KEY"
    api_key = os.getenv(key_name)
    
    if not api_key:
        raise ConfigError(f"必须在.env文件中设置 {key_name}")
        
    # 清理API密钥
    api_key = api_key.strip()
    
    # 验证API密钥格式
    if not api_key.startswith(('sk-', 'Bearer ')):
        print(f"警告: {key_name} 可能格式不正确，请确保以 'sk-' 或 'Bearer ' 开头")

    return api_key

SILICON_API_KEY = _validate_key('silicon')

# ============ 运行时配置 ============
class Config:
    # 项目根目录
    BASE_DIR = Path(__file__).parent.parent

    # 缓存目录
    CACHE_DIR = BASE_DIR / "cache"
    TEMP_DIR = CACHE_DIR / "temp"

    # 输出目录
    OUTPUT_DIR = BASE_DIR / "output"
    AUDIO_DIR = OUTPUT_DIR / "audio"
    TEXT_DIR = OUTPUT_DIR / "text"
    MINDMAP_DIR = OUTPUT_DIR / "mindmap"

    # 腾讯云配置
    TENCENT_SECRET_ID = os.getenv("TENCENT_SECRET_ID")
    TENCENT_SECRET_KEY = os.getenv("TENCENT_SECRET_KEY")
    TENCENT_APPID = os.getenv("TENCENT_APPID")

    # COS配置
    COS_REGION = "ap-guangzhou"  # 替换为你的存储桶地区
    COS_BUCKET = os.getenv("TENCENT_COS_BUCKET")  # 从环境变量获取存储桶名称

    def __init__(self):
        # 确保必要的目录存在
        for directory in [
            self.CACHE_DIR,
            self.TEMP_DIR,
            self.OUTPUT_DIR,
            self.AUDIO_DIR,
            self.TEXT_DIR,
            self.MINDMAP_DIR
        ]:
            directory.mkdir(parents=True, exist_ok=True)

        # 验证必要的环境变量
        missing_vars = []
        for var in ["TENCENT_SECRET_ID", "TENCENT_SECRET_KEY", "TENCENT_APPID", "TENCENT_COS_BUCKET"]:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            raise ValueError(f"请在 .env 文件中设置以下环境变量: {', '.join(missing_vars)}")

# 创建全局配置实例
config = Config()

# 导出所有配置变量
CACHE_DIR = config.CACHE_DIR
TEMP_DIR = config.TEMP_DIR
OUTPUT_DIR = config.OUTPUT_DIR
AUDIO_DIR = config.AUDIO_DIR
TEXT_DIR = config.TEXT_DIR
MINDMAP_DIR = config.MINDMAP_DIR
TENCENT_SECRET_ID = config.TENCENT_SECRET_ID
TENCENT_SECRET_KEY = config.TENCENT_SECRET_KEY
TENCENT_APPID = config.TENCENT_APPID
COS_REGION = config.COS_REGION
COS_BUCKET = config.COS_BUCKET

# ============ 工具函数 ============
def get_api_config(provider: Literal['silicon']) -> dict:
    """获取API配置字典"""
    if provider != 'silicon':
        raise ValueError("目前仅支持硅基流动(silicon)作为API提供商")
    return {
        'url': _API_ENDPOINTS[provider],
        'api_key': SILICON_API_KEY,
        'models': _MODEL_MAPPING[provider]
    }

def resolve_model(provider: str, version: str) -> str:
    """解析模型真实ID"""
    if provider.lower() != 'silicon':
        raise ValueError("目前仅支持硅基流动(silicon)作为API提供商")
    try:
        return _MODEL_MAPPING[provider.lower()][version.lower()]
    except KeyError:
        raise ValueError(
            f"无效的version: {version}\n"
            f"可用选项: {list(_MODEL_MAPPING[provider.lower()].keys())}"
        )

# ============ 导出配置 ============
SILICON_API_CONFIG = get_api_config('silicon')
