#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import requests
import sys
from datetime import datetime
import time
from pathlib import Path
import backoff  # 添加重试机制
import json
from typing import Optional, Dict, Any
import re
from src.config import CACHE_DIR, TEMP_DIR

# 确保可以正确从父目录导入
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# 导入配置
from src.config import config


class APIError(Exception):
    """API错误基类"""

    def __init__(self, message: str, status_code: Optional[int] = None, response_text: Optional[str] = None):
        self.message = message
        self.status_code = status_code
        self.response_text = response_text
        super().__init__(self.message)


class AuthenticationError(APIError):
    """认证错误"""
    pass


class RateLimitError(APIError):
    """速率限制错误"""
    pass


class InsufficientBalanceError(APIError):
    """余额不足错误"""
    pass


class TimeoutError(APIError):
    """超时错误"""
    pass


class MindMapGenerator:
    def __init__(self):
        from src.config import get_api_config
        self.api_config = get_api_config('silicon')  # 使用硅基流动配置
        self.model = "Pro/deepseek-ai/DeepSeek-V3"  # 使用官方模型名称
        self.mindmap_dir = config.MINDMAP_DIR
        
        if not self.api_config["api_key"]:
            raise ValueError("API key not found. Please check your .env file and SILICON_API_KEY setting.")

        # 设置API基础URL
        self.base_url = self.api_config['url']  # 使用配置文件中的URL

        # 缓存配置
        self.cache_dir = CACHE_DIR / "mindmap"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _build_prompt(self, text: str) -> str:
        """构建思维导图生成提示词"""
        return f"""请将以下文本转换为思维导图的markdown格式。要求：
## 约束:
- 遵循思维导图表达的逻辑
- markdown语法正确
- 层次清晰,形式整洁
- 零扩写：仅使用原文词汇、短语和句子，禁止任何概括或补充++
  - 组块聚合：同一段落内的相邻短句可合并为语义完整的分支节点
  - 层级展开：同一概念的三元组信息（时间+主体+数据）应作为单体节点
- 无损重点：保留所有技术术语、数据、引言和案例++
  - 数据完整：保持数字+单位+比较基准的完整结构（如"提升至92.7%相较于2022年"）
  - 引语连贯：完整保留双引号内的自然语句
- 层级还原：按原文段落顺序和逻辑关系构建分支++
  - 因果链条：用→连接前后继事件
  - 论证结构：用「前提-证据-结论」三级嵌套
- 若原文含【时间序列信息】，需要列出时间线分支++
  - 时代特征：标明世纪/年代并附加核心突破简析
- 对【未达成共识的观点】添加⚠️标记++
  - 双重标注：争议点上下级节点同步标记
- 层级还原++
  - 时间戳标注：所有章节段落起始时间必须作为节点前置标签
  - 时段覆盖：父节点标注本层级最大时段范围，子节点显示精确片段

## 时间戳整合新规则
++ 时间融合格式
- 一级节点：主题词+[起始秒-结束秒] （段落下最大覆盖时段）
- 二级节点：核心短语+[精准时段] （该小节完整时间段）
- 禁止单独出现纯时间节点
++ 时段智能衔接
1. 章节检测：每段首行时间戳自动升级为一/二级节点时段
2. 冲突处理：若相邻段时段连续，合并为父节点时段
3. 异常预警：当实际子节点时段超出父节点时，触发格式错误标记

## 新增质检指标：
✅ 组块化检验
- 验证相邻段落核心词合并率≥60%（如"国际象棋→电子游戏→思维机器研发"变为发展轨迹路径）
- 检查时间主体数据完整率：100%的定量表述必须含比较基准

✅ 衔接性核验
- 确保逻辑连接词覆盖率：每三级节点至少包含1个因果/递进关联符号（→、↑、↓）
- 节点语义完整度：单节点平均字符数应≥12（不含标点）

请只输出思维导图的markdown内容，不要添加任何额外解释、注释或其他内容。

文本内容：
{text}
"""

    def _get_cache_key(self, text: str, title: str) -> str:
        """生成缓存键"""
        import hashlib
        content_hash = hashlib.md5(text.encode()).hexdigest()
        return f"{title}_{content_hash[:8]}"

    def _load_from_cache(self, cache_key: str) -> Optional[str]:
        """从缓存加载内容"""
        cache_file = self.cache_dir / f"{cache_key}.md"
        if cache_file.exists():
            with open(cache_file, "r", encoding="utf-8") as f:
                return f.read()
        return None

    def _save_to_cache(self, cache_key: str, content: str) -> None:
        """保存内容到缓存"""
        cache_file = self.cache_dir / f"{cache_key}.md"
        with open(cache_file, "w", encoding="utf-8") as f:
            f.write(content)

    def _parse_error_response(self, response: requests.Response) -> Optional[Dict]:
        """解析错误响应"""
        try:
            return response.json()
        except:
            return None

    @backoff.on_exception(
        backoff.expo,
        (requests.exceptions.RequestException, APIError),
        max_tries=3,
        max_time=300,
        giveup=lambda e: isinstance(e, (AuthenticationError, InsufficientBalanceError))  # 认证错误和余额不足不重试
    )
    def _make_api_request(self, text: str) -> Dict[str, Any]:
        """发送API请求并处理响应"""
        try:
            payload = {
                    "model": self.model,
                    "messages": [
                        {
                            "role": "system",
                        "content": "你是一个专业的思维导图生成助手，擅长将文本转换为结构化的思维导图。"
                        },
                        {
                            "role": "user",
                        "content": self._build_prompt(text)
                    }
                ],
                "stream": False,
                "max_tokens": 4000,
                "enable_thinking": True,
                "thinking_budget": 512,
                "min_p": 0.05,
                "temperature": 0.3,
                "top_p": 0.7,
                "top_k": 50,
                "frequency_penalty": 0.5,
                "n": 1,
                "stop": []
            }

            headers = {
                "Authorization": f"Bearer {self.api_config['api_key'].strip()}",  # 确保移除可能的空白字符
                "Content-Type": "application/json",
                "Accept": "application/json"  # 明确指定接受JSON响应
            }

            print(f"正在发送请求到: {self.base_url}")
            print(f"使用模型: {self.model}")

            response = requests.post(
                url=self.base_url,
                headers=headers,
                json=payload,
                timeout=120
            )

            # 解析错误响应
            error_data = self._parse_error_response(response)

            # 检查响应
            if response.status_code == 401:
                raise AuthenticationError("API认证失败，请检查API密钥是否正确",
                                          status_code=response.status_code,
                                          response_text=response.text)
            elif response.status_code == 403:
                if error_data and error_data.get("code") == 30011:
                    raise InsufficientBalanceError(
                        "账户余额不足，无法使用付费模型。请充值后重试，或考虑使用其他可用模型。",
                        status_code=response.status_code,
                        response_text=response.text
                    )
                raise AuthenticationError("API访问被拒绝，请检查API密钥格式和权限",
                                          status_code=response.status_code,
                                          response_text=response.text)
            elif response.status_code == 429:
                raise RateLimitError("API请求超过限制，请稍后重试",
                                     status_code=response.status_code,
                                     response_text=response.text)
            elif response.status_code != 200:
                raise APIError(f"API请求失败: HTTP {response.status_code}",
                               status_code=response.status_code,
                               response_text=response.text)

            print("API原始返回：", response.json())
            return response.json()

        except requests.exceptions.Timeout:
            raise TimeoutError("API请求超时，请稍后重试")
        except requests.exceptions.ConnectionError:
            raise APIError("无法连接到API服务器，请检查网络连接")
        except json.JSONDecodeError:
            raise APIError("API返回的响应格式无效")
        except Exception as e:
            if isinstance(e, APIError):
                raise
            raise APIError(f"API请求失败: {str(e)}")

    def generate_with_deepseek(self, text: str, title: str) -> str:
        """使用硅基流动的 deepseek v3 生成思维导图"""
        try:
            print("\n使用硅基流动 DeepSeek-V3 生成思维导图...")
            
            def extract_keywords(text: str, top_k: int = 10) -> list[str]:
                """提取关键词的备选方案"""
                try:
                    import jieba.analyse
                    return jieba.analyse.extract_tags(text, topK=top_k)
                except ImportError:
                    # 如果没有安装jieba，使用简单的词频统计
                    import re
                    from collections import Counter
                    
                    # 移除标点符号和特殊字符
                    clean_text = re.sub(r'[^\w\s]', ' ', text)
                    # 分词（按空格分割）
                    words = [word for word in clean_text.split() 
                            if len(word) > 1]  # 过滤掉单字符
                    # 统计词频
                    word_freq = Counter(words)
                    # 返回出现次数最多的词
                    return [word for word, _ in word_freq.most_common(top_k)]
            
            def validate_mindmap(content: str, original_text: str) -> tuple[bool, str]:
                """验证思维导图内容的完整性和质量
                
                Returns:
                    tuple[bool, str]: (是否有效, 错误原因)
                """
                # 1. 基础结构检查
                if len(content.strip().split('\n')) < 10:
                    return False, "内容过短"
                    
                # 2. 必要章节检查
                required_sections = ['主题引入', '方法论', '核心观点']
                found_sections = [section for section in required_sections 
                                if any(line.strip().lower().find(section.lower()) != -1 
                                    for line in content.split('\n'))]
                if not found_sections:
                    return False, "缺少关键章节"
                    
                # 3. 关键词覆盖检查
                keywords = extract_keywords(original_text)
                found_keywords = [keyword for keyword in keywords 
                                if keyword in content]
                keyword_coverage = len(found_keywords) / len(keywords) if keywords else 0
                if keyword_coverage < 0.6:  # 关键词覆盖率低于60%
                    return False, f"关键词覆盖率过低({keyword_coverage:.0%})"
                    
                # 4. 层级结构检查
                levels = [len(line) - len(line.lstrip()) for line in content.split('\n') if line.strip()]
                if len(set(levels)) < 3:  # 至少应该有3个不同的层级
                    return False, "层级结构不足"
                    
                # 5. 时间戳检查（如果原文包含时间信息）
                if '[' in original_text and ']' in original_text:
                    time_pattern = r'\[\d+:\d+\]|\[\d+s-\d+s\]'
                    if not re.search(time_pattern, content):
                        return False, "缺少时间戳标注"
                
                return True, ""
                
            def generate_once() -> str:
                """单次生成思维导图内容"""
                result = self._make_api_request(text)
                if "choices" not in result or not result["choices"]:
                    raise APIError("API返回结果格式错误")
                
                mindmap_content = result["choices"][0]["message"]["content"]
                
                # 提取markdown内容
                markdown_pattern = r'```markdown\s*([\s\S]*?)\s*```'
                match = re.search(markdown_pattern, mindmap_content)
                if match:
                    mindmap_content = match.group(1).strip()
                else:
                    note_pattern = r'注：[\s\S]*$'
                    mindmap_content = re.sub(note_pattern, '', mindmap_content).strip()
                    
                # 确保标题存在
                if not mindmap_content.startswith('# '):
                    mindmap_content = f'# {title}\n\n{mindmap_content}'
                    
                return mindmap_content
                
            # 检查缓存
            cache_key = self._get_cache_key(text, title)
            mindmap_content = self._load_from_cache(cache_key)
            
            if mindmap_content:
                print("发现缓存，验证缓存内容...")
                is_valid, error = validate_mindmap(mindmap_content, text)
                if not is_valid:
                    print(f"缓存内容验证失败: {error}，重新生成...")
                    mindmap_content = None
            
            if not mindmap_content:
                print("生成新的思维导图内容...")
                # 生成两次，选择更好的版本
                attempts = []
                for i in range(2):
                    print(f"第 {i+1} 次生成...")
                    content = generate_once()
                    is_valid, error = validate_mindmap(content, text)
                    attempts.append((content, is_valid, error))
                    
                # 选择最佳结果
                valid_attempts = [a for a in attempts if a[1]]
                if valid_attempts:
                    # 如果有有效结果，选择内容最丰富的
                    mindmap_content = max(valid_attempts, 
                                        key=lambda x: len(x[0].split('\n')))[0]
                else:
                    # 如果都无效，选择内容最丰富的
                    print("警告：所有生成结果都不够理想，选择最佳结果...")
                    mindmap_content = max(attempts, 
                                        key=lambda x: len(x[0].split('\n')))[0]
                
                # 添加生成时间戳
                timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")
                header = f'<!-- Generated by Pro/deepseek-ai/DeepSeek-V3 at {timestamp} -->\n'
                mindmap_content = f'{header}\n{mindmap_content}'
                
                # 保存到缓存
                self._save_to_cache(cache_key, mindmap_content)
            
            # 保存为markdown文件
            output_path = self.mindmap_dir / f"{title}.md"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(mindmap_content)
                
            return str(output_path)
            
        except Exception as e:
            print(f"生成思维导图时出错: {str(e)}")
            raise

    def generate(self, text: str, title: str) -> str:
        """生成思维导图内容
        
        Args:
            text: 要处理的文本
            title: 思维导图标题
            
        Returns:
            str: 思维导图的 Markdown 内容
        """
        try:
            # 生成思维导图内容
            mindmap_content = f"""# {title}\n\n"""
            
            # 按段落分割文本
            paragraphs = text.split('\n\n')
            
            # 处理每个段落
            for paragraph in paragraphs:
                if paragraph.strip():
                    # 添加二级标题
                    mindmap_content += f"## {paragraph.strip()}\n\n"
            
            return mindmap_content
            
        except Exception as e:
            print(f"生成思维导图失败: {str(e)}")
            raise


if __name__ == "__main__":
    # 此处仅用于组件单独调试，实际使用时text由主程序传入
    test_text = "测试文本"  # 实际使用时会被主程序的转写内容替换
    generator = MindMapGenerator()
    result_file = generator.generate(test_text, "test")
    print(f"生成结果已保存至：{result_file}")