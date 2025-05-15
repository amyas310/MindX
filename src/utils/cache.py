import os
import json
import hashlib
from typing import Any, Optional
from ..config import TEMP_DIR

class Cache:
    def __init__(self, cache_dir: str = os.path.join(TEMP_DIR, 'cache')):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        
    def _get_cache_key(self, data: str) -> str:
        """生成缓存键"""
        return hashlib.md5(data.encode('utf-8')).hexdigest()
    
    def _get_cache_path(self, key: str) -> str:
        """获取缓存文件路径"""
        return os.path.join(self.cache_dir, f"{key}.json")
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存数据"""
        cache_path = self._get_cache_path(key)
        if os.path.exists(cache_path):
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return None
        return None
    
    def set(self, key: str, value: Any) -> None:
        """设置缓存数据"""
        cache_path = self._get_cache_path(key)
        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(value, f, ensure_ascii=False, indent=2)
        except:
            pass 