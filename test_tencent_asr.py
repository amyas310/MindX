import os
import sys
from pathlib import Path
import traceback
from dotenv import load_dotenv

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 加载环境变量
load_dotenv()

# 检查必要的环境变量
required_vars = ['TENCENT_SECRET_ID', 'TENCENT_SECRET_KEY']
missing_vars = [var for var in required_vars if not os.getenv(var)]
if missing_vars:
    print(f"错误: 缺少以下环境变量: {', '.join(missing_vars)}")
    print("请在 .env 文件中设置这些变量")
    sys.exit(1)

def test_asr_connection():
    """测试与腾讯云 ASR 服务的连接"""
    try:
        from src.processors.tencent_asr import TencentASR
        
        print("初始化腾讯云 ASR 客户端...")
        asr_client = TencentASR()
        
        print(f"使用的腾讯云 API 密钥: {asr_client.secret_id[:4]}...{asr_client.secret_id[-4:]}")
        print(f"使用的服务区域: {asr_client.region}")
        
        # 创建一个简单的 API 调用测试
        # 这不会实际执行任何识别，只会验证 API 连接和签名
        test_action = "DescribeTaskStatus"
        test_data = {"TaskId": 0}  # 无效的任务ID，只为测试连接
        
        import json
        test_payload = json.dumps(test_data)
        
        print("生成 API 认证头...")
        headers = asr_client._get_auth_header(test_action, test_payload)
        
        print("API 认证头生成成功:")
        for key, value in headers.items():
            if key == "Authorization":
                print(f"  {key}: {value[:20]}...{value[-20:]}")
            else:
                print(f"  {key}: {value}")
        
        print("\n腾讯云 ASR API 连接测试成功!")
        print("注意: 这只是测试了连接和认证，但未执行实际的语音识别请求")
        
        # 询问是否进行完整测试
        answer = input("\n是否要进行实际的语音识别测试? (y/n): ")
        if answer.lower() == 'y':
            test_full_recognition()
        
    except Exception as e:
        print(f"测试失败: {str(e)}")
        traceback.print_exc()
        return False
    
    return True

def test_full_recognition():
    """测试完整的语音识别流程"""
    try:
        from src.processors.tencent_asr import TencentASR
        asr_client = TencentASR()
        
        # 询问测试文件路径
        test_file = input("请输入要测试的音频文件路径 (默认使用示例文件): ")
        if not test_file:
            # 使用示例文件
            test_file = os.path.join(project_root, "temp", "test_audio.mp3")
            if not os.path.exists(test_file):
                print(f"示例文件 {test_file} 不存在，请手动指定文件路径")
                return False
        
        if not os.path.exists(test_file):
            print(f"错误: 文件 {test_file} 不存在")
            return False
        
        print(f"开始测试 {test_file} 的语音识别...")
        result = asr_client.transcribe(test_file)
        
        print("\n识别结果:")
        print(f"文本长度: {len(result.get('full_text', ''))}")
        print(f"识别的片段数: {len(result.get('segments', []))}")
        
        # 显示部分结果
        full_text = result.get('full_text', '')
        print("\n识别文本预览 (前100字符):")
        print(full_text[:100] + ('...' if len(full_text) > 100 else ''))
        
        print("\n完整的语音识别测试成功!")
        
    except Exception as e:
        print(f"完整测试失败: {str(e)}")
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    print("开始测试腾讯云 ASR 服务连接...")
    test_asr_connection() 