import os
import json
import time
import hashlib
import hmac
import base64
from datetime import datetime
from pathlib import Path
from http.client import HTTPSConnection
from urllib.parse import quote
import math
from concurrent.futures import ThreadPoolExecutor, as_completed

from tqdm import tqdm
from pydub import AudioSegment

from src.config import config
from src.utils.cos_uploader import COSUploader # 确保这个模块存在且COSUploader已实现

from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.asr.v20190614 import asr_client, models
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException

class TencentASR:
    def __init__(self):
        self.secret_id = config.TENCENT_SECRET_ID
        self.secret_key = config.TENCENT_SECRET_KEY
        if not self.secret_id or not self.secret_key:
            raise ValueError("腾讯云 API 密钥未设置，请在 .env 文件中添加 TENCENT_SECRET_ID 和 TENCENT_SECRET_KEY")

        self.appid = os.getenv("TENCENT_APPID")
        if not self.appid:
            raise ValueError("腾讯云 APPID 未设置，请在 .env 文件中添加 TENCENT_APPID")

        cred = credential.Credential(self.secret_id, self.secret_key)
        http_profile = HttpProfile()
        http_profile.endpoint = "asr.tencentcloudapi.com"
        client_profile = ClientProfile()
        client_profile.httpProfile = http_profile
        self.client = asr_client.AsrClient(cred, "ap-guangzhou", client_profile)

        self.service = "asr"
        self.host = "asr.tencentcloudapi.com"
        self.version = "2019-06-14"
        self.region = "ap-guangzhou"

        self.cache_dir = config.CACHE_DIR / "tencent_asr"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.cos_uploader = COSUploader()
        
        self.poll_interval_seconds = getattr(config, 'TENCENT_ASR_POLL_INTERVAL', 10) # 轮询间隔
        self.max_wait_minutes = getattr(config, 'TENCENT_ASR_MAX_WAIT_MINUTES', 30) # 最大等待时间

    def _sign(self, key, msg):
        return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()

    def _get_auth_header(self, action, payload_str):
        algorithm = "TC3-HMAC-SHA256"
        timestamp = int(time.time())
        date = datetime.utcfromtimestamp(timestamp).strftime("%Y-%m-%d")

        http_request_method = "POST"
        canonical_uri = "/"
        canonical_querystring = ""
        ct = "application/json; charset=utf-8"
        canonical_headers = f"content-type:{ct}\nhost:{self.host}\nx-tc-action:{action.lower()}\n"
        signed_headers = "content-type;host;x-tc-action"
        
        hashed_request_payload = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()
        canonical_request = (http_request_method + "\n" +
                             canonical_uri + "\n" +
                             canonical_querystring + "\n" +
                             canonical_headers + "\n" +
                             signed_headers + "\n" +
                             hashed_request_payload)

        credential_scope = date + "/" + self.service + "/" + "tc3_request"
        hashed_canonical_request = hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()
        string_to_sign = (algorithm + "\n" +
                          str(timestamp) + "\n" +
                          credential_scope + "\n" +
                          hashed_canonical_request)

        secret_date = self._sign(("TC3" + self.secret_key).encode("utf-8"), date)
        secret_service = self._sign(secret_date, self.service)
        secret_signing = self._sign(secret_service, "tc3_request")
        signature = hmac.new(secret_signing, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()

        authorization = (algorithm + " " +
                         "Credential=" + self.secret_id + "/" + credential_scope + ", " +
                         "SignedHeaders=" + signed_headers + ", " +
                         "Signature=" + signature)

        headers = {
            "Authorization": authorization,
            "Content-Type": ct,
            "Host": self.host,
            "X-TC-Action": action,
            "X-TC-Timestamp": str(timestamp),
            "X-TC-Version": self.version
        }
        if self.region:
            headers["X-TC-Region"] = self.region
        return headers

    def get_recognition_result(self, task_id: int) -> dict:
        """获取语音识别结果 (使用手动HTTP请求方式)"""
        action = "DescribeTaskStatus"
        request_data = {"TaskId": task_id}
        payload_str = json.dumps(request_data)
        headers = self._get_auth_header(action, payload_str)

        try:
            conn = HTTPSConnection(self.host)
            conn.request("POST", "/", headers=headers, body=payload_str.encode("utf-8"))
            response = conn.getresponse()
            result_content = response.read().decode("utf-8")
            conn.close()
            
            result_json = json.loads(result_content)

            if "Response" in result_json and "Error" in result_json["Response"] and result_json["Response"]["Error"]:
                error = result_json["Response"]["Error"]
                print(f"获取任务 {task_id} 状态失败: {error.get('Code')} - {error.get('Message')}")
                return {"success": False, "error_info": error, "raw_response": result_json}
            
            # 返回原始的 Response 部分，让调用者解析 Data
            return {"success": True, "response_data": result_json.get("Response", {})}

        except Exception as e:
            print(f"调用DescribeTaskStatus接口异常 (TaskId: {task_id}): {e}")
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}

    def _split_audio(self, audio_path: str, segment_duration_ms: int = 10 * 60 * 1000) -> list:
        print(f"开始分割音频文件: {audio_path}")
        try:
            audio = AudioSegment.from_file(audio_path)
            duration_ms = len(audio)

            if duration_ms <= segment_duration_ms:
                print("音频时长未超过限制，无需分割。")
                return [audio_path]

            chunks = []
            num_segments = math.ceil(duration_ms / segment_duration_ms)
            
            output_dir = Path(audio_path).parent / f"{Path(audio_path).stem}_chunks"
            output_dir.mkdir(parents=True, exist_ok=True)
            base_name = Path(audio_path).stem
            audio_format = Path(audio_path).suffix.lstrip('.') or "mp3" # Default to mp3 if no suffix

            print(f"音频总时长: {duration_ms / 1000 / 60:.2f} 分钟. 将分割为 {num_segments} 个片段.")
            
            for i in range(num_segments):
                start_ms = i * segment_duration_ms
                end_ms = min((i + 1) * segment_duration_ms, duration_ms)
                chunk_audio = audio[start_ms:end_ms]
                
                chunk_filename = output_dir / f"{base_name}_chunk{i+1}.{audio_format}"
                chunk_audio.export(chunk_filename, format=audio_format)
                chunks.append(str(chunk_filename))
                print(f"已保存分片: {chunk_filename}")
            
            return chunks
        except Exception as e:
            print(f"分割音频失败: {e}")
            import traceback
            traceback.print_exc()
            raise

    def _transcribe_single(self, audio_path_or_url: str, engine_model_type: str = "16k_zh") -> dict:
        print(f"\n处理单个音频: {audio_path_or_url}")
        cos_audio_url = ""
        is_url = str(audio_path_or_url).startswith(('http://', 'https://'))

        if not is_url:
            if not os.path.exists(audio_path_or_url):
                return {"success": False, "text": None, "error": f"本地文件不存在: {audio_path_or_url}"}
            print(f"上传本地文件 {audio_path_or_url} 到COS...")
            try:
                cos_audio_url = self.cos_uploader.upload(audio_path_or_url)
                if not cos_audio_url:
                    return {"success": False, "text": None, "error": f"上传文件到COS失败: {audio_path_or_url}"}
                print(f"文件上传至COS: {cos_audio_url}")
            except Exception as e:
                return {"success": False, "text": None, "error": f"上传文件到COS异常: {str(e)}"}
        else:
            cos_audio_url = quote(audio_path_or_url, safe=':/')
            print(f"使用已编码的URL: {cos_audio_url}")
        
        try:
            req = models.CreateRecTaskRequest()
            params = {
                "EngineModelType": engine_model_type,
                "ChannelNum": 1,
                "ResTextFormat": 0,
                "SourceType": 0,
                "Url": cos_audio_url
            }
            req.from_json_string(json.dumps(params))
            
            print(f"创建ASR任务，请求参数: {params}")
            resp = self.client.CreateRecTask(req)
            task_id = resp.Data.TaskId
            print(f"任务创建成功，ID: {task_id}")

            max_polls = (self.max_wait_minutes * 60) // self.poll_interval_seconds
            for i in range(max_polls):
                time.sleep(self.poll_interval_seconds)
                print(f"查询任务 {task_id} 状态 (尝试 {i+1}/{max_polls})...")
                
                # 使用我们手动实现的 get_recognition_result
                status_result = self.get_recognition_result(task_id)

                if not status_result.get("success"):
                    error_detail = status_result.get("error", "获取状态失败")
                    if "error_info" in status_result: # More detailed error from API
                         error_detail = f"{status_result['error_info'].get('Code')} - {status_result['error_info'].get('Message')}"
                    return {"success": False, "text": None, "error": f"获取任务状态失败: {error_detail}"}

                response_data = status_result.get("response_data", {}).get("Data", status_result.get("response_data", {}))
                if not response_data : # Check if Data is empty or not present
                    print(f"任务 {task_id} 状态查询结果中无有效Data字段。原始响应: {status_result.get('response_data')}")
                    # Potentially retry or handle as error
                    continue # Or return error if this state is unexpected

                task_status = response_data.get("Status")
                status_str = response_data.get("StatusStr", "未知状态字符串")
                
                print(f"任务 {task_id} 当前状态: {task_status} ({status_str})")

                if task_status == 2:
                    transcribed_text = response_data.get("Result", "")
                    print(f"\n任务 {task_id} 转写完成！")
                    return {"success": True, "text": transcribed_text, "error": None}
                elif task_status == 3:
                    error_message = response_data.get("ErrorMsg", "未知错误")
                    print(f"\n任务 {task_id} 转写失败: {error_message}")
                    return {"success": False, "text": None, "error": error_message}
            
            return {"success": False, "text": None, "error": f"任务 {task_id} 超时未完成。"}

        except TencentCloudSDKException as sdk_err:
            print(f"腾讯云SDK错误 (CreateRecTask): {sdk_err}")
            return {"success": False, "text": None, "error": str(sdk_err)}
        except Exception as e:
            print(f"处理单个音频转写时发生意外错误: {str(e)}")
            import traceback
            traceback.print_exc()
            return {"success": False, "text": None, "error": str(e)}

    def transcribe(self, audio_path_or_url: str, engine_model_type: str = "16k_zh") -> dict:
        print(f"\n开始完整转写流程: {audio_path_or_url}")
        is_url = str(audio_path_or_url).startswith(('http://', 'https://'))
        file_size_mb_limit = getattr(config, 'TENCENT_ASR_FILE_SPLIT_THRESHOLD_MB', 500)
        
        try:
            if not is_url:
                if not os.path.exists(audio_path_or_url):
                    return {"success": False, "text": None, "error": f"文件不存在: {audio_path_or_url}"}
                
                file_size_bytes = os.path.getsize(audio_path_or_url)
                file_size_mb = file_size_bytes / (1024 * 1024)
                print(f"本地音频文件大小: {file_size_mb:.2f}MB")

                if file_size_mb > file_size_mb_limit:
                    print(f"文件大小超过 {file_size_mb_limit}MB，将进行分片处理。")
                    audio_chunks_paths = self._split_audio(audio_path_or_url)
                    
                    all_results_text = []
                    max_workers = getattr(config, 'TENCENT_ASR_MAX_CONCURRENT_TASKS', 2)
                    
                    chunk_results_futures = []
                    with ThreadPoolExecutor(max_workers=max_workers) as executor:
                        for chunk_path in audio_chunks_paths:
                            future = executor.submit(self._transcribe_single, chunk_path, engine_model_type)
                            chunk_results_futures.append(future)
                        
                        for future in tqdm(as_completed(chunk_results_futures), total=len(audio_chunks_paths), desc="处理音频分片"):
                            try:
                                chunk_result = future.result()
                                if chunk_result.get("success"):
                                    all_results_text.append(chunk_result.get("text", ""))
                                else:
                                    error_msg = chunk_result.get("error", "未知错误")
                                    # Find which chunk this was, for logging (can be complex if order isn't guaranteed)
                                    print(f"一个音频分片处理失败: {error_msg}") 
                                    all_results_text.append(f"[分片转写失败: {error_msg}]")
                            except Exception as exc:
                                print(f"一个音频分片执行时发生异常: {exc}")
                                all_results_text.append(f"[分片转写异常: {exc}]")
                    
                    # 清理分片文件和目录
                    if audio_chunks_paths and audio_chunks_paths[0] != audio_path_or_url : # Ensure it's actually chunked
                        chunk_dir_path = Path(audio_chunks_paths[0]).parent
                        for chunk_file in audio_chunks_paths:
                            try:
                                if Path(chunk_file).exists():
                                    os.remove(chunk_file)
                                    print(f"已清理分片文件: {chunk_file}")
                            except Exception as e:
                                print(f"清理分片文件 {chunk_file} 失败: {e}")
                        try:
                            if chunk_dir_path.exists() and not any(chunk_dir_path.iterdir()):
                                chunk_dir_path.rmdir()
                                print(f"已清理分片目录: {chunk_dir_path}")
                        except Exception as e:
                            print(f"清理分片目录 {chunk_dir_path} 失败: {e}")
                                
                    final_text = "\n".join(all_results_text)
                    return {"success": True, "text": final_text, "error": None}
                else:
                    print("文件大小在限制内，直接处理单个文件。")
                    return self._transcribe_single(audio_path_or_url, engine_model_type)
            else:
                print("输入为URL，直接提交给ASR服务处理。")
                return self._transcribe_single(audio_path_or_url, engine_model_type)

        except Exception as e:
            error_msg = str(e)
            print(f"完整音频转写过程出错: {error_msg}")
            import traceback
            traceback.print_exc()
            return {"success": False, "text": None, "error": error_msg}
