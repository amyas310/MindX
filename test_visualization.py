1
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import webbrowser
import platform
import subprocess
from pathlib import Path
from src.utils.markmap_visualizer import MarkdownVisualizer


def open_in_browser(file_path: str) -> None:
    """在浏览器中打开文件"""
    file_url = f"file://{Path(file_path).resolve()}"
    
    system = platform.system()
    try:
        if system == 'Darwin':  # macOS
            # 尝试使用 Chrome
            try:
                subprocess.run(['open', '-a', 'Google Chrome', file_url])
            except:
                # 如果 Chrome 打开失败，使用默认浏览器
                subprocess.run(['open', file_url])
        elif system == 'Windows':
            # Windows 系统下尝试使用 Chrome
            chrome_paths = [
                r'C:\Program Files\Google\Chrome\Application\chrome.exe',
                r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe'
            ]
            for path in chrome_paths:
                if os.path.exists(path):
                    subprocess.run([path, file_url])
                    break
            else:
                # 如果没有找到 Chrome，使用默认浏览器
                webbrowser.open(file_url)
        else:  # Linux 或其他系统
            try:
                subprocess.run(['google-chrome', file_url])
            except FileNotFoundError:
                webbrowser.open(file_url)
    except Exception as e:
        print(f"无法自动打开浏览器，请手动打开文件：{file_url}")
        print(f"错误信息：{str(e)}")


def test_single_file():
    """测试单个文件的可视化"""
    # 测试文件路径
    test_file = "/Users/yytt/PycharmProjects/everything to xmind/output/mindmap/P30｜2—17君子喻於義，小人喻於利｜楊立華｜四書精讀.md"
    
    try:
        visualizer = MarkdownVisualizer()
        # 使用 visualize 方法而不是 visualize_file
        result = visualizer.visualize(test_file)
        print(f"可视化文件已生成并打开：{result}")
    except Exception as e:
        print(f"处理出错：{str(e)}")


def test_batch():
    """批量测试文件夹下的所有 markdown 文件"""
    mindmap_dir = Path("/Users/yytt/PycharmProjects/everything to xmind/output/mindmap")
    
    try:
        visualizer = MarkdownVisualizer()
        for md_file in mindmap_dir.glob("*.md"):
            result = visualizer.visualize(str(md_file))
            print(f"已处理：{md_file.name}")
    except Exception as e:
        print(f"批量处理出错：{str(e)}")


def main():
    print("1. 测试单个文件")
    print("2. 批量测试")
    choice = input("请选择操作（1/2）：")
    
    if choice == "1":
        test_single_file()
    elif choice == "2":
        test_batch()
    else:
        print("无效的选择")


if __name__ == "__main__":
    main()