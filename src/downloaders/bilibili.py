import os
from pathlib import Path
import subprocess
import re
import traceback
from pydub import AudioSegment
from ..config import config

class BilibiliDownloader:
    def __init__(self):
        self.temp_dir = config.CACHE_DIR / "bilibili"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
    def download(self, url: str) -> dict:
        """下载B站视频"""
        try:
            video_path = self._download_video(url)
            
            if not os.path.exists(video_path):
                raise Exception(f"视频下载失败: {video_path}")
            
            # 获取视频标题
            title = Path(video_path).stem
            
            # 转换音频格式
            print("正在转换音频格式...")
            audio = AudioSegment.from_file(video_path)
            audio = audio.set_channels(1).set_frame_rate(16000)
            
            # 生成音频文件路径，直接保存到output目录
            audio_path = config.OUTPUT_DIR / "audio" / f"{title}.mp3"
            audio.export(
                audio_path,
                format="mp3",
                parameters=[
                    "-ac", "1",        # 单声道
                    "-ar", "16000",    # 16kHz采样率
                    "-b:a", "48k"      # 48kbps比特率
                ]
            )
            
            # 删除原始视频文件
            os.remove(video_path)
            print(f"音频格式转换完成: {audio_path}")
            
            return {
                'title': title,
                'audio': str(audio_path)
            }
            
        except Exception as e:
            print(f"下载过程中出错: {str(e)}")
            traceback.print_exc()
            raise Exception(f"B站下载失败: {str(e)}")
            
    def _download_video(self, url: str) -> str:
        """使用you-get下载B站视频"""
        # 因为浏览器Cookie问题，B站下载建议直接使用you-get或annie工具
        # 假设系统中已安装了you-get
        
        output_dir = str(self.temp_dir)
        
        # 检查是否安装了you-get
        try:
            subprocess.run(["you-get", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        except (subprocess.SubprocessError, FileNotFoundError):
            raise Exception("需要安装 you-get 工具来下载B站视频，请执行: pip install you-get")
            
        print(f"正在使用 you-get 下载B站视频: {url}")
        
        # 使用you-get下载视频
        try:
            result = subprocess.run(
                ["you-get", "-o", output_dir, url],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )
            
            # 从输出中提取下载的文件路径
            output = result.stdout + result.stderr
            # 一般you-get会在下载完成后显示保存路径
            match = re.search(r'Saving to: (.+?)\.', output)
            if match:
                video_path = match.group(1).strip() + ".flv"  # B站常用flv格式
                if os.path.exists(video_path):
                    return video_path
                    
            # 如果无法从输出中提取路径，尝试查找最近修改的视频文件
            video_files = []
            for ext in ['.flv', '.mp4', '.webm']:
                video_files.extend(list(Path(output_dir).glob(f"*{ext}")))
                
            if video_files:
                # 按修改时间排序，取最新的
                video_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                return str(video_files[0])
                
            raise Exception("无法定位下载的视频文件")
            
        except subprocess.CalledProcessError as e:
            print(f"you-get 下载失败: {e.stderr}")
            raise Exception(f"B站下载失败: {e.stderr}")