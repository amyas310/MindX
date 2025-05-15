#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import traceback
import hashlib
from pathlib import Path
from typing import Tuple, List, Optional # 确保 Optional 已导入
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm
import re
import json
import time

from src.config import config
from src.downloaders.youtube import YouTubeDownloader
from src.downloaders.bilibili import BilibiliDownloader
from src.downloaders.xiaoyuzhou import XiaoyuzhouDownloader
from src.processors.audio import AudioProcessor
from src.translators.translator import Translator
from src.utils.mindmap import MindMapGenerator
from src.utils.progress import ProgressBar
from src.utils.cos_uploader import COSUploader

class ContentProcessor:
    """内容处理器，统一处理各种来源的内容"""
    
    def __init__(self):
        # 初始化目录
        self.temp_dir = config.TEMP_DIR
        self.cache_dir = config.CACHE_DIR
        self.output_dir = config.OUTPUT_DIR
        self.audio_dir = config.AUDIO_DIR
        self.text_dir = config.TEXT_DIR
        self.mindmap_dir = config.MINDMAP_DIR
        self.youtube_cache_dir = self.cache_dir / "youtube" # 新增初始化
        
        # 确保所有目录存在
        for directory in [self.temp_dir, self.cache_dir, self.output_dir, 
                         self.audio_dir, self.text_dir, self.mindmap_dir,
                         self.youtube_cache_dir]: # 添加 youtube_cache_dir 到检查列表
            directory.mkdir(parents=True, exist_ok=True)
        
        # 初始化处理器
        self.audio_processor = AudioProcessor()
        self.translator = Translator()
        self.mindmap_generator = MindMapGenerator()
        self.cos_uploader = COSUploader()
        
        # 初始化下载器映射
        self.downloaders = {
            "youtube": YouTubeDownloader(),
            "bilibili": BilibiliDownloader(),
            "xiaoyuzhou": XiaoyuzhouDownloader()
        }
        
    def detect_url_type(self, url: str) -> str:
        """检测URL类型"""
        if not url:
            return "unknown"
            
        url = url.lower()
        for platform in self.downloaders.keys():
            if platform in url:
                return platform
        return "unknown"
        
    def is_chinese(self, text: str) -> bool:
        """判断文本是否主要为中文"""
        chinese_chars = sum(1 for char in text if '\u4e00' <= char <= '\u9fff')
        return chinese_chars / len(text) > 0.5

    def _get_youtube_video_id(self, url: str) -> Optional[str]:
        """
        从URL中提取YouTube视频ID。
        支持以下格式:
        - http://www.youtube.com/watch?v=VIDEO_ID
        - http://youtube.com/watch?v=VIDEO_ID
        - https://m.youtube.com/watch?v=VIDEO_ID
        - https://youtu.be/VIDEO_ID
        - https://www.youtube.com/embed/VIDEO_ID
        - https://www.youtube.com/v/VIDEO_ID
        - https://www.youtube.com/shorts/VIDEO_ID
        """
        if not url:
            return None
        
        # 确保 re 模块已导入 (通常在文件顶部导入)
        # import re

        patterns = [
            r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/watch\?v=([a-zA-Z0-9_-]{11})',
            r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/embed\/([a-zA-Z0-9_-]{11})',
            r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/v\/([a-zA-Z0-9_-]{11})',
            r'(?:https?:\/\/)?youtu\.be\/([a-zA-Z0-9_-]{11})',
            r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/shorts\/([a-zA-Z0-9_-]{11})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    def _get_file_hash(self, file_path: str) -> str:
        """计算文件的MD5哈希值"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
        
    def _get_cache_path(self, file_hash: str, suffix: str) -> Path:
        """获取缓存文件路径"""
        return self.cache_dir / f"{file_hash}{suffix}"
        
    def process_content(self, url: str) -> Tuple[str, Optional[str], str]:
        """处理内容的主要流程
        
        Returns:
            Tuple[str, Optional[str], str]: (原始文本内容, 中文翻译文本内容 或 None, 思维导图文件路径)
        """
        import time # 这个导入可以移到文件顶部
        start_time = time.time()
        
        original_text: str = ""
        translated_text: Optional[str] = None
        mindmap_file_path: str = ""
        
        try:
            url_type = self.detect_url_type(url)
            if url_type == "unknown":
                raise ValueError("不支持的URL格式")
            
            steps = ['下载音频', 'ASR转写', '翻译(如果需要)', '生成思维导图', '清理文件'] # 更新步骤
            progress = ProgressBar(len(steps), prefix="处理进度")
            
            # 1. 下载并提取音频
            result = self._download_content(url)
            if not result:
                raise ValueError("下载内容失败")
                
            print(f"下载耗时: {time.time()-start_time:.2f}秒")
            progress.print(1)
            
            # 2. 检查音频文件缓存
            audio_path = result['audio']
            audio_hash = self._get_file_hash(audio_path)
            cos_cache_path = self._get_cache_path(audio_hash, ".cos_url")
            
            if cos_cache_path.exists():
                print("发现COS缓存，直接使用已上传的文件")
                with open(cos_cache_path, "r") as f:
                    cos_url = f.read().strip()
            else:
                cos_url = self.cos_uploader.upload(audio_path)
                with open(cos_cache_path, "w") as f:
                    f.write(cos_url)
                    
            print(f"音频文件URL: {cos_url}")
            
            # 3. 检查转写缓存
            asr_cache_path = self._get_cache_path(audio_hash, ".asr")
            if asr_cache_path.exists():
                print("发现转写缓存，直接使用已有的转写结果")
                with open(asr_cache_path, "r", encoding="utf-8") as f:
                    original_text = f.read()
            else:
                # ASR转写
                transcription = self.audio_processor.tencent_asr.transcribe(cos_url)
                if not transcription or not transcription.get('success'):
                    error_msg = transcription.get('error', '未知错误') if transcription else '转写失败'
                    raise ValueError(f"转写失败: {error_msg}")
                
                original_text = transcription.get('text', '')
                if not original_text:
                    raise ValueError("转写结果为空")
                
                with open(asr_cache_path, "w", encoding="utf-8") as f:
                    f.write(original_text)
            
            progress.print(2)

            # 3.1 翻译 (如果原文不是中文)
            if original_text and not self.is_chinese(original_text):
                print("\n检测到非中文内容，尝试翻译成中文...")
                try:
                    print(f"DEBUG: 原文待翻译 (前100字符): '{original_text[:100]}...'") # 新增日志
                    # 假设 self.translator.translate 方法存在并返回翻译后的字符串
                    # 您可能需要指定目标语言，例如 target_lang='zh-CN' 或 'zh'
                    translated_text = self.translator.translate(original_text)
                    if translated_text:
                        print(f"DEBUG: 翻译完成。译文 (前100字符): '{translated_text[:100]}...'") # 新增日志
                    else:
                        print("DEBUG: 翻译结果为空。") # 新增日志
                        # translated_text will be None or empty string from here
                except Exception as e:
                    print(f"DEBUG: 翻译时发生错误: {e}") # 新增日志
                    # 非致命错误，继续执行，只是 translated_text 会是 None
            elif original_text and self.is_chinese(original_text): # 新增else-if分支用于日志
                print("\nDEBUG: 内容已是中文，无需翻译。")
            elif not original_text: # 新增else-if分支用于日志
                print("\nDEBUG: 原文内容为空，无法翻译。")
            progress.print(3) # 更新进度条步骤

            # 保存文本 (原始文本)
            title = result.get('title', 'untitled')
            text_path = self.text_dir / f"{title}.txt"
            with open(text_path, "w", encoding="utf-8") as f:
                f.write(original_text)
            
            # 4. 使用硅基流动的deepseek v3生成思维导图
            print("\n使用硅基流动的deepseek v3生成思维导图...")
            # 优先使用翻译后的文本生成思维导图，如果翻译文本不存在或翻译失败，则使用原始文本
            text_for_mindmap = translated_text if translated_text else original_text
            if not text_for_mindmap: # 新增检查
                print("警告: 用于生成思维导图的文本为空!") # 新增日志
            mindmap_file_path = self.mindmap_generator.generate_with_deepseek(text_for_mindmap, title)
            progress.print(4) # 更新进度条步骤
            
            # 5. 清理临时文件
            self._cleanup_files(audio_path)
            progress.print(5) # 更新进度条步骤
            
            return original_text, translated_text, mindmap_file_path
            
        except Exception as e:
            error_msg = str(e)
            if "语音识别服务余额不足" in error_msg:
                print("\n" + "="*50)
                print(error_msg)
                print("="*50)
            else:
                print(f"\n处理出错: {error_msg}")
                print("详细错误信息:")
                traceback.print_exc()
            raise Exception(f"处理失败: {error_msg}")
        
    def _download_content(self, url: str) -> Optional[dict]:
        """下载内容，增加YouTube缓存逻辑"""
        url_type = self.detect_url_type(url)
        print(f"\n1. 从{url_type}下载并提取音频...")
        
        if url_type == "youtube":
            video_id = self._get_youtube_video_id(url)
            if video_id:
                cache_file_path = self.youtube_cache_dir / f"{video_id}.json"
                if cache_file_path.exists():
                    try:
                        with open(cache_file_path, "r", encoding="utf-8") as f:
                            cache_data = json.load(f)
                        cached_audio_path_str = cache_data.get("audio_path")
                        cached_title = cache_data.get("title")
                        
                        if cached_audio_path_str and cached_title:
                            cached_audio_path = Path(cached_audio_path_str)
                            if cached_audio_path.exists():
                                print(f"发现YouTube视频缓存 (ID: {video_id})，使用缓存文件: {cached_audio_path}")
                                return {'audio': str(cached_audio_path), 'title': cached_title}
                            else:
                                print(f"缓存记录中的音频文件不存在: {cached_audio_path_str}，将重新下载。")
                        else:
                            print(f"YouTube缓存文件 {cache_file_path} 格式不正确，将重新下载。")
                    except Exception as e:
                        print(f"读取YouTube缓存文件 {cache_file_path} 失败: {e}，将重新下载。")
            else:
                print("未能从URL中提取有效的YouTube视频ID，无法使用缓存。")

        downloader = self.downloaders.get(url_type)
        if not downloader:
            print(f"未找到针对 {url_type} 的下载器。")
            return None
            
        try:
            result = downloader.download(url)
            
            if not isinstance(result, dict):
                raise ValueError("下载器返回格式错误")
            
            if 'audio' not in result:
                raise ValueError("下载器未返回音频文件路径")
            
            if 'title' not in result:
                result['title'] = Path(result['audio']).stem
            
            # 如果是YouTube下载成功，且获取到了video_id，则写入缓存
            if url_type == "youtube" and video_id and result:
                cache_file_path = self.youtube_cache_dir / f"{video_id}.json"
                try:
                    cache_data = {
                        "audio_path": str(Path(result['audio']).resolve()), # 存储绝对路径
                        "title": result['title'],
                        "original_url": url,
                        "cached_at": time.strftime("%Y-%m-%d %H:%M:%S")
                    }
                    with open(cache_file_path, "w", encoding="utf-8") as f:
                        json.dump(cache_data, f, ensure_ascii=False, indent=4)
                    print(f"YouTube视频下载结果已缓存到: {cache_file_path}")
                except Exception as e:
                    print(f"写入YouTube缓存文件 {cache_file_path} 失败: {e}")
                    
            return result
            
        except Exception as e:
            print(f"下载失败: {str(e)}")
            # 可以在这里打印更详细的traceback
            # import traceback
            # traceback.print_exc()
            return None

    def _cleanup_files(self, audio_path: str):
        """清理临时文件"""
        try:
            if os.path.exists(audio_path):
                os.remove(audio_path)
        except Exception as e:
            print(f"清理文件失败: {str(e)}")

def main():
    """主函数"""
    processor = ContentProcessor()
    
    while True:
        try:
            url = input("请输入链接：")
            if url.lower() == 'exit':
                break
                
            if not url:
                continue
                
            text, mindmap_file = processor.process_content(url)
            print(f"\n处理完成!")
            print(f"思维导图文件: {mindmap_file}")
            
        except Exception as e:
            print(f"\n错误: {str(e)}")
            print("请重新尝试，或输入 'exit' 退出程序")
            continue

if __name__ == "__main__":
    main()
