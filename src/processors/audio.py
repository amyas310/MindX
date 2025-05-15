import os
import traceback
from pathlib import Path
from pydub import AudioSegment
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor
import math
from ..config import config
from .tencent_asr import TencentASR
import logging
import yt_dlp
from src.utils.mindmap import MindMapGenerator
from src.utils.cos_uploader import COSUploader
from src.config import OUTPUT_DIR, AUDIO_DIR, TEXT_DIR, MINDMAP_DIR

logging.basicConfig(level=logging.DEBUG)


class AudioProcessor:
    """音频处理类，负责提取音频和转写"""
    
    def __init__(self):
        """初始化音频处理器"""
        from ..config import config
        # 确保所有必要的目录都存在
        self.temp_dir = config.TEMP_DIR / "audio"
        self.cache_dir = config.CACHE_DIR / "audio"
        self.output_dir = config.OUTPUT_DIR / "audio"
        self.splits_dir = self.cache_dir / "splits"
        
        # 创建所有必要的目录
        for directory in [self.temp_dir, self.cache_dir, self.output_dir, self.splits_dir]:
            directory.mkdir(parents=True, exist_ok=True)
    
        # 初始化ASR客户端
        self.tencent_asr = TencentASR()
        self.mindmap_generator = MindMapGenerator()
        self.cos_uploader = COSUploader()

    def _split_audio(self, audio_path, max_size_mb=90):
        """将音频文件分割成小于指定大小的片段"""
        try:
            # 加载音频文件
            print(f"\n正在加载音频文件: {audio_path}")
            audio = AudioSegment.from_file(audio_path)

            # 计算需要分成几片
            file_size = os.path.getsize(audio_path)
            max_size_bytes = max_size_mb * 1024 * 1024
            num_chunks = math.ceil(file_size / max_size_bytes)

            if num_chunks == 1:
                return [audio_path]

            # 计算每片的时长（毫秒）
            chunk_length_ms = len(audio) // num_chunks

            # 创建临时目录存放分片
            temp_dir = self.cache_dir / "splits"
            temp_dir.mkdir(parents=True, exist_ok=True)

            # 分割音频
            print(f"音频将被分割为 {num_chunks} 个片段")
            chunks = []
            for i in range(num_chunks):
                start_ms = i * chunk_length_ms
                end_ms = min((i + 1) * chunk_length_ms, len(audio))

                chunk = audio[start_ms:end_ms]
                chunk_path = temp_dir / f"chunk_{i + 1}.mp3"

                print(f"正在导出第 {i + 1}/{num_chunks} 个片段...")
                chunk.export(
                    chunk_path,
                    format="mp3",
                    parameters=[
                        "-ac", "1",  # 单声道
                        "-ar", "16000",  # 16kHz采样率
                        "-b:a", "48k"  # 48kbps比特率
                    ]
                )
                chunks.append(str(chunk_path))

            return chunks

        except Exception as e:
            print(f"分割音频失败: {e}")
            raise

    def extract_audio(self, input_path, output_path, sample_rate=16000):
        """从输入文件提取音频并进行格式转换
        
        Args:
            input_path: 输入文件路径
            output_path: 输出音频路径
            sample_rate: 采样率，默认16000Hz
            
        Returns:
            str: 处理后的音频文件路径
        """
        try:
            input_path = Path(input_path)
            if not input_path.exists():
                raise FileNotFoundError(f"文件未找到: {input_path}")
                
            # 检查文件大小限制（1GB）
            file_size = os.path.getsize(input_path)
            if file_size > 1024 * 1024 * 1024:
                raise ValueError(f"文件过大: {file_size / 1024 / 1024:.1f}MB > 1024MB")

            # 生成输出音频路径
            output_path = Path(output_path)
            if output_path.exists():
                print(f"已存在处理后的音频: {output_path}")
                return str(output_path)
                
            print(f"正在处理音频: {input_path}")
            print(f"源文件大小: {file_size / 1024 / 1024:.1f}MB")

            # 检测是否为音频文件
            audio_extensions = {'.mp3', '.wav', '.m4a', '.aac', '.ogg', '.flac'}
            is_audio = input_path.suffix.lower() in audio_extensions
            
            # 使用 pydub 处理音频
            audio = AudioSegment.from_file(str(input_path))
            
            # 获取当前音频参数
            current_channels = audio.channels
            current_sample_rate = audio.frame_rate
            current_duration = len(audio) / 1000  # 转换为秒

            print(f"音频信息: {current_channels}声道, {current_sample_rate}Hz, {current_duration:.1f}秒")

            # 只有在需要时才进行转换
            if current_channels != 1 or current_sample_rate != sample_rate:
                print(f"转换音频格式: {current_channels}声道@{current_sample_rate}Hz -> 单声道@{sample_rate}Hz")
                audio = audio.set_channels(1).set_frame_rate(sample_rate)
            
            # 导出为指定格式，使用较低的比特率以确保文件大小合适
            print("导出音频文件...")
            audio.export(
                output_path,
                format="mp3",
                parameters=[
                    "-ac", "1",  # 单声道
                    "-ar", str(sample_rate),  # 采样率
                    "-b:a", "48k",  # 比特率设为48kbps
                ]
            )

            # 检查处理后的文件大小
            output_size = os.path.getsize(output_path)
            print(f"处理后文件大小: {output_size / 1024 / 1024:.1f}MB")

            # 验证处理后的音频
            processed_audio = AudioSegment.from_file(str(output_path))
            if processed_audio.channels != 1 or processed_audio.frame_rate != sample_rate:
                raise ValueError(
                    f"音频处理失败: 处理后的音频格式不符合要求 ({processed_audio.channels}声道@{processed_audio.frame_rate}Hz)")
            
            print(f"音频已处理并保存为: {output_path}")
            return str(output_path)
            
        except Exception as e:
            print(f"处理音频时出错: {e}")
            traceback.print_exc()
            raise
    
    def process_audio(self, audio_path: str) -> list:
        """处理音频文件，返回分片信息列表

        Args:
            audio_path: 音频文件路径

        Returns:
            分片信息列表，每个分片包含：
            {
                'index': 分片索引,
                'cos_url': COS URL,
                'start_time': 开始时间(ms),
                'end_time': 结束时间(ms),
                'duration': 时长(ms)
            }
        """
        try:
            print(f"\n开始处理音频: {Path(audio_path).name}")

            # 获取文件大小
            file_size = os.path.getsize(audio_path)
            print(f"音频文件大小: {file_size / 1024 / 1024:.1f}MB")

            # 加载音频文件以获取时长信息
            audio = AudioSegment.from_file(audio_path)
            total_duration = len(audio)

            # 如果文件大于90MB，进行分片处理
            if file_size > 90 * 1024 * 1024:
                print("文件大小超过90MB，将进行分片处理")

                # 分割音频
                chunk_paths = self._split_audio(audio_path)

                # 并行上传所有分片到COS
                chunk_infos = []

                with ThreadPoolExecutor(max_workers=5) as executor:
                    # 计算每个分片的时间信息
                    chunk_length_ms = total_duration // len(chunk_paths)

                    # 创建上传任务
                    upload_futures = {}
                    for i, chunk_path in enumerate(chunk_paths):
                        start_time = i * chunk_length_ms
                        end_time = min((i + 1) * chunk_length_ms, total_duration)

                        future = executor.submit(self.tencent_asr.cos_uploader.upload, chunk_path)
                        upload_futures[future] = {
                            'index': i,
                            'path': chunk_path,
                            'start_time': start_time,
                            'end_time': end_time,
                            'duration': end_time - start_time
                        }

                    # 收集上传结果
                    for future in upload_futures:
                        try:
                            info = upload_futures[future]
                            cos_url = future.result()

                            chunk_info = {
                                'index': info['index'],
                                'cos_url': cos_url,
                                'start_time': info['start_time'],
                                'end_time': info['end_time'],
                                'duration': info['duration']
                            }

                            chunk_infos.append(chunk_info)
                            print(f"分片 {info['index'] + 1} 上传成功: {cos_url}")
                        except Exception as e:
                            print(f"分片 {info['index'] + 1} 上传失败: {e}")

                    # 按索引排序
                    chunk_infos.sort(key=lambda x: x['index'])
        
                    # 清理临时文件
                    for chunk_path in chunk_paths:
                        try:
                            os.remove(chunk_path)
                        except:
                            pass

                    return chunk_infos
            else:
                # 文件不大，直接上传
                print("文件大小适中，不需要分片")
                cos_url = self.tencent_asr.cos_uploader.upload(audio_path)
                return [{
                    'index': 0,
                    'cos_url': cos_url,
                    'start_time': 0,
                    'end_time': total_duration,
                    'duration': total_duration
                }]

        except Exception as e:
            print(f"处理音频失败: {e}")
            raise

    def validate_audio_format(self, audio_path):
        """验证音频格式是否符合要求"""
        try:
            audio = AudioSegment.from_file(str(audio_path))
            output_path = Path(audio_path).parent / f"validated_{Path(audio_path).name}"
            
            # 统一设置格式
            audio = audio.set_channels(1)  # 单声道
            audio = audio.set_frame_rate(16000)  # 16kHz采样率
            
            # 导出时使用较低的比特率
            audio.export(
                output_path,
                format="mp3",
                parameters=[
                    "-b:a", "48k",  # 48kbps比特率
                    "-ac", "1",  # 单声道
                    "-ar", "16000"  # 16kHz采样率
                ]
            )
            
            print(f"音频格式已标准化: {output_path}")
            return str(output_path)
            
        except Exception as e:
            print(f"音频格式验证失败: {e}")
            return audio_path

    def process_content(self, url: str):
        """处理音视频内容
        
        Args:
            url: YouTube视频链接或音频文件URL
            
        Returns:
            tuple: (转写文本, 思维导图文件路径, None)
        """
        try:
            # 判断是否是B站链接
            if "bilibili.com" in url:
                audio_path = self._download_bilibili(url)
            # 判断是否是YouTube链接
            elif "youtube.com" in url or "youtu.be" in url:
                audio_path = self._download_youtube(url)
            else:
                # 假设是直接的音频URL
                audio_path = url

            # 如果是本地文件，先上传到COS
            if not audio_path.startswith(('http://', 'https://')):
                print(f"上传音频文件到COS: {audio_path}")
                audio_path = self.cos_uploader.upload(audio_path)
                print(f"上传成功，COS URL: {audio_path}")

            # 进行语音识别
            result = self.tencent_asr.transcribe(audio_path)
            if not result["success"]:
                raise ValueError(result["error"])
            
            text = result["text"]
            if not text:
                raise ValueError("转写结果为空")

            # 生成输出文件名（使用URL的最后一部分作为基础名）
            base_name = url.split('/')[-1].split('?')[0]
            if not base_name:
                base_name = f"output_{int(time.time())}"

            # 保存文本文件
            text_file = TEXT_DIR / f"{base_name}.txt"
            with open(text_file, "w", encoding="utf-8") as f:
                f.write(text)

            # 生成思维导图
            mindmap_file = MINDMAP_DIR / f"{base_name}.md"
            mindmap_content = self.mindmap_generator.generate(text, base_name)
            with open(mindmap_file, "w", encoding="utf-8") as f:
                f.write(mindmap_content)

            return text, str(mindmap_file), None

        except Exception as e:
            import traceback
            traceback.print_exc()
            raise ValueError(str(e))

    def _download_youtube(self, url: str) -> str:
        """下载YouTube视频的音频"""
        try:
            ydl_opts = {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'outtmpl': str(AUDIO_DIR / '%(title)s.%(ext)s'),
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                audio_file = AUDIO_DIR / f"{info['title']}.mp3"
                return str(audio_file)

        except Exception as e:
            raise ValueError(f"YouTube下载失败: {str(e)}")

    def _download_bilibili(self, url: str) -> str:
        """下载B站视频的音频"""
        try:
            ydl_opts = {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'outtmpl': str(AUDIO_DIR / '%(title)s.%(ext)s'),
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                audio_file = AUDIO_DIR / f"{info['title']}.mp3"
                return str(audio_file)

        except Exception as e:
            raise ValueError(f"B站视频下载失败: {str(e)}")