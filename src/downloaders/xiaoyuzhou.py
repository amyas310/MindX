import os
from pathlib import Path
import requests
import json
import re
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import traceback
from tqdm import tqdm
from ..config import config
from pydub import AudioSegment

class XiaoyuzhouDownloader:
    """小宇宙播客下载器"""

    def __init__(self):
        """初始化下载器"""
        self.temp_dir = config.CACHE_DIR / "xiaoyuzhou"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36'
        }

    def download(self, url: str) -> dict:
        """下载小宇宙播客
        
        Args:
            url: 小宇宙播客链接
            
        Returns:
            dict: {
                'title': str,          # 内容标题
                'audio': str,          # 音频文件路径
                'description': str,    # 内容描述
                'podcast_title': str   # 播客标题
            }
        """
        try:
            print("步骤 1: 获取播客信息...")
            episode_info = self._get_episode_info(url)
            
            print("步骤 2: 准备文件路径...")
            sanitized_title = self._sanitize_filename(episode_info['title'])
            # 直接保存到output目录
            audio_path = config.OUTPUT_DIR / "audio" / f"{sanitized_title}.mp3"
            print(f"调试：音频将保存为: {audio_path}")
            
            print("步骤 3: 下载音频...")
            if not audio_path.exists():
                self._download_file(
                    episode_info['audio_url'],
                    audio_path,
                    desc=f"[{episode_info['podcast_title']}] {episode_info['title']}"
                )
            else:
                print(f"音频文件已存在，跳过下载: {audio_path}")

            return {
                'title': episode_info['title'],
                'audio': str(audio_path),
                'description': episode_info.get('description', ''),
                'podcast_title': episode_info.get('podcast_title', '未知播客')
            }

        except Exception as e:
            print(f"下载失败: {str(e)}")
            traceback.print_exc()
            raise Exception(f"小宇宙下载失败: {str(e)}")

    def _get_episode_info(self, url: str) -> dict:
        """获取播客单集信息"""
        try:
            if not self._validate_url(url):
                raise ValueError("无效的小宇宙播客链接")

            print(f"调试：正在请求 URL: {url}")
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            html = response.text
            soup = BeautifulSoup(html, 'html.parser')
            print("调试：页面HTML获取并解析成功")

            # 从 <script type="application/ld+json"> 获取信息
            ld_json_script = soup.find('script', type='application/ld+json')
            if ld_json_script and ld_json_script.string:
                json_data = json.loads(ld_json_script.string)
                
                audio_url = json_data.get('associatedMedia', {}).get('contentUrl')
                title = json_data.get('name')
                podcast_info = json_data.get('partOfSeries', {})
                podcast_title = podcast_info.get('name')
                description = json_data.get('description', '')

                if audio_url and title and podcast_title:
                    print("调试：通过 <script type='application/ld+json'> 找到信息")
                    return {
                        'title': title,
                        'audio_url': audio_url,
                        'description': description,
                        'podcast_title': podcast_title
                    }

            raise ValueError("无法在页面中找到有效的音频信息")

        except Exception as e:
            raise Exception(f"获取播客信息失败: {str(e)}")

    def _validate_url(self, url: str) -> bool:
        """验证URL是否为有效的小宇宙链接"""
        try:
            parsed = urlparse(url)
            return all([
                parsed.scheme in ['http', 'https'],
                'xiaoyuzhoufm.com' in parsed.netloc,
                '/episode/' in parsed.path
            ])
        except Exception:
            return False

    def _sanitize_filename(self, filename: str) -> str:
        """清理文件名，移除不合法字符"""
        filename = re.sub(r'[\\/*?:"<>|]', '', filename)
        return filename[:100].strip()

    def _download_file(self, url: str, file_path: Path, desc: str = "") -> None:
        """下载文件并显示进度"""
        print(f"调试：开始下载文件到 {file_path}")
        response = requests.get(url, headers=self.headers, stream=True)
        response.raise_for_status()

        total_size = int(response.headers.get('content-length', 0))
        block_size = 8192
        
        try:
            # 首先下载到临时文件
            temp_file = file_path.with_suffix('.temp')
            with tqdm(total=total_size, unit='B', unit_scale=True, desc=desc) as pbar:
                with open(temp_file, 'wb') as f:
                    for data in response.iter_content(block_size):
                        f.write(data)
                        pbar.update(len(data))

            print(f"{desc} 下载完成，正在转换音频格式...")
            
            # 使用 pydub 转换音频格式
            audio = AudioSegment.from_file(temp_file)
            audio = audio.set_channels(1).set_frame_rate(16000)
            audio.export(
                file_path,
                format="mp3",
                parameters=[
                    "-ac", "1",        # 单声道
                    "-ar", "16000",    # 16kHz采样率
                    "-b:a", "48k"      # 48kbps比特率
                ]
            )
            
            # 删除临时文件
            temp_file.unlink()
            print(f"音频格式转换完成: {file_path}")

        except Exception as e:
            print(f"\n下载或转换过程中发生错误: {e}")
            if temp_file.exists():
                temp_file.unlink()
            if file_path.exists():
                file_path.unlink()
            raise

