from src.processors.tencent_asr import TencentASR
from src.utils.markdown_visualizer import MarkdownVisualizer
import json
from http.client import HTTPSConnection
from pathlib import Path
import webbrowser
import time

def test_visualization():
    """测试思维导图可视化"""
    try:
        # 创建可视化器实例
        visualizer = MarkdownVisualizer()
        
        # 指定要处理的文件路径
        base_dir = Path("/Users/yytt/PycharmProjects/everything to xmind")
        markdown_file = base_dir / "output/mindmap/P30｜2—17君子喻於義，小人喻於利｜楊立華｜四書精讀.md"
        
        if not markdown_file.exists():
            raise FileNotFoundError(f"找不到文件：{markdown_file}")
            
        # 生成可视化
        print("\n开始生成思维导图可视化...")
        output_file = visualizer.visualize_file(str(markdown_file))
        print(f"可视化文件已生成：{output_file}")
        
        # 自动打开浏览器
        file_url = f"file://{Path(output_file).resolve()}"
        print(f"正在打开浏览器查看结果...")
        webbrowser.open(file_url)
        
    except Exception as e:
        print(f"可视化处理出错：{str(e)}")
        import traceback
        traceback.print_exc()

def test_asr_with_url():
    try:
        # 初始化ASR客户端
        asr = TencentASR()
        
        # 音频文件URL
        audio_url = "https://etm-1303057600.cos.ap-guangzhou.myqcloud.com/audio/1746241588_-1323244645609892899.mp3"
        
        # 构建请求数据 (最小化参数)
        request_data = {
            "EngineModelType": "16k_zh",
            "ChannelNum": 1,
            "ResTextFormat": 0,  # 使用最简单的格式0
            "SourceType": 0,
            "Url": audio_url
        }
        
        # 生成认证头
        action = "CreateRecTask"
        payload = json.dumps(request_data)
        headers = asr._get_auth_header(action, payload)
        
        print("开始创建识别任务 (使用最小化参数)...")
        conn = HTTPSConnection(asr.host)
        conn.request("POST", "/", headers=headers, body=payload.encode("utf-8"))
        response = conn.getresponse()
        result = json.loads(response.read().decode("utf-8"))
        
        if "Response" in result and "Data" in result["Response"]:
            task_id = result["Response"]["Data"]["TaskId"]
            print(f"任务创建成功，ID: {task_id}")
            print("开始获取识别结果...")
            
            # 每10秒检查一次结果，最多等待5分钟
            for i in range(30):
                result = asr.get_recognition_result(task_id)
                status = result.get("Status")
                
                if status == 2:  # 任务完成
                    print("\n转写完成！")
                    print("识别结果：")
                    print(result.get("Result", ""))
                    break
                elif status == 3:  # 任务失败
                    print(f"\n转写失败: {result.get('ErrorMessage', '未知错误')}")
                    break
                else:
                    # 增加状态码打印，方便调试
                    print(f"等待结果，当前状态: {status}，已等待 {(i+1)*10} 秒...")
                    import time
                    time.sleep(10)
            # 如果循环结束仍未完成或失败
            if status not in [2, 3]:
                 print(f"\n任务超时或状态未知 (最终状态: {status})")
        else:
            error_msg = result.get("Response", {}).get("Error", {}).get("Message", "未知错误")
            request_id = result.get("Response", {}).get("RequestId", "N/A")
            print(f"创建任务失败: {error_msg} (RequestId: {request_id})")
            
    except Exception as e:
        print(f"测试过程出错: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # 测试思维导图可视化
    print("开始测试思维导图可视化...")
    test_visualization()
    
    # 如果还需要测试 ASR，取消下面的注释
    # print("\n开始测试ASR服务 (最小化参数)...")
    # test_asr_with_url() 