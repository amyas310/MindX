#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import json
import webbrowser
import subprocess
from pathlib import Path
from datetime import datetime

class MarkMapVisualizer:
    """
    Markmap可视化器, 将markdown文本转换为可交互的思维导图。
    使用markmap-lib库实现高质量的思维导图可视化。
    """
    
    def __init__(self):
        self.html_template = '''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>{title}</title>
            <style>
                body {{ 
                    margin: 0;
                    padding: 0;
                    height: 100vh;
                    font-family: "Microsoft YaHei", Arial, sans-serif;
                }}
                #markmap {{
                    width: 100%;
                    height: 100vh;
                }}
            </style>
            <script src="https://cdn.jsdelivr.net/npm/d3@6"></script>
            <script src="https://cdn.jsdelivr.net/npm/markmap-view@0.15.4"></script>
        </head>
        <body>
            <div id="markmap"></div>
            <script>
                const markdown = {markdown_content};
                const options = {{ 
                    color: '#555',
                    autoFit: true,
                    initialExpandLevel: 2,
                    duration: 500, 
                    maxWidth: 500,
                    faviconColor: '#555',
                    zoom: true,
                }};
                
                document.addEventListener('DOMContentLoaded', function() {{
                    const {{ Markmap, loadCSS, loadJS }} = window.markmap;
                    
                    // 初始化markmap
                    const mm = Markmap.create('#markmap', options, markdown);
                    
                    // 添加快捷键支持
                    document.addEventListener('keydown', function(e) {{
                        switch(e.key) {{
                            case '0':
                            case ' ':
                                // 自适应窗口
                                mm.fit();
                                break;
                            case '+':
                                // 放大
                                mm.setZoom(mm.getZoom() * 1.2);
                                break;
                            case '-':
                                // 缩小
                                mm.setZoom(mm.getZoom() / 1.2);
                                break;
                            case '.':
                                // 折叠到第一级
                                mm.setOptions({{...options, initialExpandLevel: 1}});
                                mm.renderData(markdown);
                                break;
                            case ',':
                                // 重置到原始树
                                mm.setOptions({{...options, initialExpandLevel: 2}});
                                mm.renderData(markdown);
                                break;
                            case 'm':
                                // 只显示中心/显示全部
                                const currLevel = mm.options.initialExpandLevel;
                                mm.setOptions({{...options, initialExpandLevel: currLevel === 1 ? 99 : 1}});
                                mm.renderData(markdown);
                                break;
                            default:
                                // 展开到指定级别 (1-9)
                                if (e.key >= '1' && e.key <= '9') {{
                                    const level = parseInt(e.key);
                                    mm.setOptions({{...options, initialExpandLevel: level}});
                                    mm.renderData(markdown);
                                }}
                        }}
                    }});
                }});
            </script>
        </body>
        </html>
        '''
        
        # 确保安装了markmap-lib
        try:
            # 检查markmap-lib是否已安装
            subprocess.run(['markmap', '--version'], capture_output=True, check=False)
        except FileNotFoundError:
            print("markmap-lib 未安装，将使用CDN加载必要的库。")
            print("如需完整功能，请使用 pip install markmap-lib 安装。")
    
    def create_visualization(self, markdown_content: str, output_path: str) -> str:
        """创建思维导图可视化文件
        
        Args:
            markdown_content: Markdown格式的思维导图内容
            output_path: 输出HTML文件路径
        
        Returns:
            str: 输出文件的完整路径
        """
        # 确保是绝对路径
        output_path = os.path.abspath(output_path)
        
        # 从markdown提取标题
        title_match = re.search(r'^# (.*?)$', markdown_content, re.MULTILINE)
        title = title_match.group(1) if title_match else "思维导图"
        
        # 将markdown内容转换为JSON字符串以嵌入到HTML
        markdown_json = json.dumps(markdown_content)
        
        # 生成HTML内容
        html_content = self.html_template.format(
            title=title,
            markdown_content=markdown_json
        )
        
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # 写入HTML文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
            
        return output_path
    
    def create_visualization_with_title(self, markdown_content: str, title: str) -> str:
        """使用指定标题创建思维导图可视化文件
        
        Args:
            markdown_content: Markdown格式的思维导图内容
            title: 文件标题和输出文件名
            
        Returns:
            str: 输出文件的完整路径
        """
        # 创建输出目录
        output_dir = Path('output/visualization')
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 构建输出文件路径
        output_path = output_dir / f"{title}.html"
        
        return self.create_visualization(markdown_content, str(output_path))
        
    def visualize(self, markdown_file: str) -> str:
        """读取markdown文件并创建可视化
        
        Args:
            markdown_file: Markdown文件路径
            
        Returns:
            str: 输出文件的完整路径
        """
        with open(markdown_file, 'r', encoding='utf-8') as f:
            markdown_content = f.read()
        
        # 获取输入文件信息
        input_path = Path(markdown_file)
        title = input_path.stem
        
        # 创建输出目录
        output_dir = Path('output/visualization')
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 构建输出文件路径
        output_path = output_dir / f"{title}.html"
        
        # 创建可视化文件
        result_file = self.create_visualization(markdown_content, str(output_path))
        
        # 在浏览器中打开文件
        file_url = f'file://{os.path.abspath(result_file)}'
        webbrowser.open(file_url)
        
        return result_file


if __name__ == "__main__":
    # 测试代码
    test_md = """# 测试思维导图
    
## 一级节点1
- 二级节点1.1
  - 三级节点1.1.1
  - 三级节点1.1.2
- 二级节点1.2

## 一级节点2
- 二级节点2.1
- 二级节点2.2
  - 三级节点2.2.1
    - 四级节点2.2.1.1
"""
    visualizer = MarkMapVisualizer()
    output = visualizer.create_visualization_with_title(test_md, "测试思维导图")
    print(f"生成思维导图: {output}")
    
    # 在浏览器中打开
    file_url = f'file://{os.path.abspath(output)}'
    webbrowser.open(file_url)