#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from pathlib import Path
import traceback
import yt_dlp
import sys
import time
import warnings
import browser_cookie3
warnings.filterwarnings('ignore', category=Warning)

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from src.config import config

class YouTubeDownloader:
    def __init__(self):
        self.temp_dir = config.CACHE_DIR / "youtube"
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def _get_browser_cookies(self):
        """从浏览器获取 cookies"""
        try:
            # 尝试从不同浏览器获取 cookies
            browsers = [
                ('chrome', browser_cookie3.chrome),
                ('firefox', browser_cookie3.firefox),
                ('safari', browser_cookie3.safari),
            ]
            
            for browser_name, browser_func in browsers:
                try:
                    cookies = browser_func(domain_name='youtube.com')
                    print(f"成功从 {browser_name} 获取 cookies")
                    return cookies
                except Exception as e:
                    print(f"从 {browser_name} 获取cookies失败: {str(e)}")
                    continue
            
            print("无法从任何浏览器获取 cookies")
            return None
        except Exception as e:
            print(f"获取 cookies 时出错: {str(e)}")
            return None

    def _write_netscape_cookies(self, cookies, cookie_file):
        """将 cookies 写入 Netscape 格式的文件"""
        try:
            with open(cookie_file, 'w', encoding='utf-8') as f:
                f.write("# Netscape HTTP Cookie File\n")
                f.write("# https://curl.haxx.se/rfc/cookie_spec.html\n")
                f.write("# This is a generated file!  Do not edit.\n\n")
                
                for cookie in cookies:
                    secure = "TRUE" if cookie.secure else "FALSE"
                    expires = int(time.time() + 365*24*3600) if cookie.expires is None else cookie.expires
                    row = f"{cookie.domain}\tTRUE\t{cookie.path}\t{secure}\t{expires}\t{cookie.name}\t{cookie.value}\n"
                    f.write(row)
            print(f"Cookies已保存到: {cookie_file}")
            return True
        except Exception as e:
            print(f"保存cookies文件失败: {str(e)}")
            return False

    def download(self, url: str) -> dict:
        """下载 YouTube 视频并转换为音频格式
        
        Args:
            url: YouTube视频URL
            
        Returns:
            dict: {
                'title': 视频标题,
                'audio': 音频文件路径
            }
        """
        try:
            print("\n=== YouTube下载测试 ===")
            print(f"测试URL: {url}")
            
            # 尝试自动获取cookies
            cookies = self._get_browser_cookies()
            cookies_file = self.temp_dir / "youtube_cookies.txt"
            
            if cookies:
                print("正在保存浏览器cookies...")
                self._write_netscape_cookies(cookies, cookies_file)
            
            # 设置下载选项
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': str(config.OUTPUT_DIR / "audio" / '%(title)s.%(ext)s'),
                'verbose': True,
                'progress': True,
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '48'
                }],
                # FFmpeg全局参数
                'postprocessor_args': [
                    # 音频处理参数
                    '-ar', '16000',     # 采样率16kHz
                    '-ac', '1',         # 单声道
                    '-b:a', '48k',      # 比特率48kbps
                    '-codec:a', 'mp3',  # 使用mp3编码器
                    '-write_xing', '1'  # 添加VBR标签
                ],
                # 下载重试设置
                'retries': 10,
                'fragment_retries': 10,
                'skip_unavailable_fragments': True,
                'ignoreerrors': False,
                # 网络设置
                'socket_timeout': 30,
                'extractor_retries': 3,
                # 添加HTTP头
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-us,en;q=0.5',
                    'Sec-Fetch-Mode': 'navigate',
                },
                'nocheckcertificate': True
            }
            
            # 添加cookies文件(如果存在)
            if cookies_file.exists():
                print(f"使用cookies文件: {cookies_file}")
                ydl_opts['cookiefile'] = str(cookies_file)

            print("\n开始下载 YouTube 视频...")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                try:
                    # 获取视频信息
                    info = ydl.extract_info(url, download=True)
                    
                    # 处理播放列表情况
                    if 'entries' in info:
                        info = info['entries'][0]
                    
                    title = info.get('title', '').strip()
                    if not title:
                        raise ValueError("无法获取视频标题")
                    
                    # 获取音频文件路径
                    audio_path = str(config.OUTPUT_DIR / "audio" / f"{title}.mp3")
                    
                    # 验证文件是否存在
                    if not os.path.exists(audio_path):
                        # 检查是否有其他格式的文件
                        possible_files = list(config.OUTPUT_DIR.glob(f"audio/{title}.*"))
                        if possible_files:
                            audio_path = str(possible_files[0])
                        else:
                            raise FileNotFoundError("音频文件未生成")
                    
                    print(f"\n下载完成: {audio_path}")
                    return {
                        'title': title,
                        'audio': audio_path
                    }
                    
                except yt_dlp.utils.DownloadError as e:
                    error_msg = str(e)
                    if "HTTP Error 403" in error_msg:
                        print("\n检测到 403 错误，尝试更新 yt-dlp...")
                        os.system("pip install --upgrade yt-dlp")
                        print("yt-dlp 更新完成，请重试下载")
                        
                        # 如果没有cookies，提示用户
                        if not cookies_file.exists():
                            print("\n提示：下载失败可能是因为需要登录。请尝试以下方法：")
                            print("1. 确保您已在浏览器中登录YouTube")
                            print("2. 如果仍然失败，可能需要手动导出cookies：")
                            print("   a. 安装浏览器扩展'EditThisCookie'或'Cookie-Editor'")
                            print("   b. 访问YouTube并确保您已登录")
                            print("   c. 通过扩展导出cookies为Netscape格式")
                            print(f"   d. 将cookies保存到: {cookies_file}")
                            
                    raise Exception(f"下载失败: {error_msg}")
                except Exception as e:
                    raise Exception(f"处理失败: {str(e)}")

        except Exception as e:
            error_msg = f"YouTube下载失败: {str(e)}"
            print(f"\n下载过程中出错: {error_msg}")
            traceback.print_exc()
            raise Exception(error_msg)
        finally:
            # 清理cookies文件
            if cookies_file.exists():
                try:
                    os.remove(cookies_file)
                    print("已清理临时cookies文件")
                except Exception as e:
                    print(f"清理cookies文件失败: {str(e)}")