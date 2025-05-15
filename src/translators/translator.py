import requests
from typing import Optional
from src.config import SILICON_API_CONFIG

class Translator:
    """翻译器类，使用硅基流动API进行翻译"""
    
    def __init__(self):
        self.config = SILICON_API_CONFIG
        self.model = "Pro/deepseek-ai/DeepSeek-V3"  # 使用V3模型
        
        if not self.config['api_key']:
            raise ValueError("API密钥未设置，请检查配置")

    def translate(self, text: str) -> str: # 注意：main.py调用时传入了target_lang='zh'，但这里未接收。不过当前硬编码为中文翻译，暂不影响。
        """翻译文本为中文
        
        Args:
            text: 要翻译的文本
            
        Returns:
            str: 翻译后的中文文本
            
        Raises:
            Exception: 当翻译失败时抛出异常
        """
        headers = {
            "Authorization": f"Bearer {self.config['api_key'].strip()}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        try:
            # 构建翻译提示词
            prompt = (
                "你是一个专业的翻译官，请将以下内容准确流畅地翻译成中文，"
                "保持专业术语的准确性和上下文的连贯性:\n\n{text}"
            ).format(text=text)

            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "top_p": 0.7,
                "frequency_penalty": 0.5,
                "presence_penalty": 0.5
            }
            
            print(f"DEBUG: Translator: 发送翻译请求到 {self.config['url']} 模型 {self.model}") # 新增日志
            # print(f"DEBUG: Translator: 请求Payload: {payload}") # 可以取消注释以查看完整payload，但注意可能包含大量文本

            response = requests.post(
                self.config["url"],
                json=payload,
                headers=headers,
                timeout=120
            )
            
            print(f"DEBUG: Translator: API响应状态码: {response.status_code}") # 新增日志
            # print(f"DEBUG: Translator: API响应头: {response.headers}") # 新增日志
            
            # 检查响应状态
            if response.status_code == 401:
                raise Exception("API认证失败，请检查API密钥")
            elif response.status_code == 403:
                error_data = response.json()
                print(f"DEBUG: Translator: API 403 错误详情: {error_data}") # 新增日志
                if error_data.get("code") == 30011:
                    raise Exception("账户余额不足，请充值后重试")
                raise Exception("API访问被拒绝，请检查API密钥权限")
            elif response.status_code == 429:
                raise Exception("API请求超过限制，请稍后重试")
            
            response.raise_for_status() # 其他4xx/5xx错误会在这里抛出
            result = response.json()
            print(f"DEBUG: Translator: API原始返回JSON: {result}") # 新增日志
            
            if "choices" not in result or not result["choices"]:
                print("DEBUG: Translator: API返回结果格式错误: 'choices' 缺失或为空") # 新增日志
                raise Exception("API返回结果格式错误")
            
            translation_content = result["choices"][0]["message"]["content"]
            print(f"DEBUG: Translator: 提取的翻译内容 (前100字符): '{translation_content[:100]}...'") # 新增日志
            return translation_content

        except requests.exceptions.Timeout:
            print("DEBUG: Translator: 翻译请求超时") # 新增日志
            raise Exception("翻译请求超时，请稍后重试")
        except requests.exceptions.ConnectionError:
            print("DEBUG: Translator: 无法连接到API服务器") # 新增日志
            raise Exception("无法连接到API服务器，请检查网络连接")
        except Exception as e:
            error_msg = f"翻译失败: {str(e)}"
            if hasattr(e, 'response') and e.response:
                try:
                    # print(f"DEBUG: Translator: 翻译失败时API响应内容: {e.response.text}") # 新增日志
                    error_data = e.response.json()
                    if error_data.get("message"):
                        error_msg += f"\n详细信息: {error_data['message']}"
                except:
                    pass # 避免解析JSON失败时再次抛错
            print(f"DEBUG: Translator.translate 内部捕获并重新抛出错误: {error_msg}") # 新增日志
            raise Exception(error_msg)
