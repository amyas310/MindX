#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import json
import webbrowser
from pathlib import Path
from datetime import datetime

class MarkMapVisualizer:
    """
    Markmap可视化器, 将markdown文本转换为可交互的思维导图。
    使用纯前端方式实现，无需依赖markmap-lib库。
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
                .tip {{
                    position: fixed;
                    top: 10px;
                    right: 10px;
                    background: rgba(0,0,0,0.6);
                    color: white;
                    padding: 8px 12px;
                    border-radius: 4px;
                    font-size: 14px;
                    z-index: 100;
                    transition: opacity 0.3s;
                    opacity: 0.8;
                }}
                .tip:hover {{
                    opacity: 1;
                }}
                .tip ul {{
                    margin: 5px 0;
                    padding-left: 20px;
                }}
            </style>
            <script src="https://cdn.jsdelivr.net/npm/d3@6.7.0"></script>
            <script src="https://cdn.jsdelivr.net/npm/markmap-view@0.14.4"></script>
        </head>
        <body>
            <div id="markmap"></div>
            <div class="tip">
                快捷键:
                <ul>
                    <li>空格: 适应窗口</li>
                    <li>+/-: 放大/缩小</li>
                    <li>1-9: 展开层级</li>
                </ul>
            </div>
            <script>
                // 将markdown内容直接嵌入到HTML中
                const markdown = {markdown_content};
                
                window.onload = function() {{
                    // 移除提示信息
                    setTimeout(function() {{
                        const tip = document.querySelector('.tip');
                        if (tip) {{
                            tip.style.opacity = '0';
                            setTimeout(() => tip.remove(), 300);
                        }}
                    }}, 8000);
                    
                    // 创建markmap
                    const {{ Markmap, loadCSS, loadJS }} = window.markmap;
                    const options = {{ 
                        color: '#555',
                        autoFit: true,
                        initialExpandLevel: 2, 
                        maxWidth: 500,
                        duration: 500,
                        zoom: true,
                    }};
                    
                    // 简单转换markdown到markmap结构
                    function parseMarkdown(md) {{
                        const lines = md.split('\\n');
                        const root = {{ 
                            content: '思维导图',
                            children: []
                        }};
                        
                        let current = root;
                        let stack = [root];
                        let lastLevel = 0;
                        
                        for (const line of lines) {{
                            if (!line.trim()) continue;
                            
                            // 确定标题级别
                            let level = 0;
                            let content = line;
                            
                            if (line.startsWith('#')) {{
                                const match = line.match(/^(#+)\\s+(.*)/);
                                if (match) {{
                                    level = match[1].length;
                                    content = match[2];
                                    
                                    // 根节点 - 替换主标题
                                    if (level === 1) {{
                                        root.content = content;
                                        continue;
                        }}
                                }}
                            }} else if (line.trim().startsWith('-')) {{
                                // 列表项
                                const match = line.match(/^(\\s*-\\s+)(.*)/);
                                if (match) {{
                                    const indent = line.indexOf('-') / 2;
                                    level = indent + 2; // 列表项的层级从2开始
                                    content = match[2];
                                }}
                            }} else {{
                                continue; // 跳过不是标题或列表的行
                            }}
                            
                            if (level === 0) continue;
                            
                            // 创建新节点
                            const node = {{ content, children: [] }};
                            
                            // 调整堆栈，找到正确的父节点
                            if (level > lastLevel) {{
                                // 深入层级
                                stack.push(current);
                            }} else if (level < lastLevel) {{
                                // 返回上层
                                const steps = lastLevel - level + 1;
                                for (let i = 0; i < steps && stack.length > 1; i++) {{
                                    stack.pop();
                        }}
                            }}
                            
                            // 添加到当前父节点
                            current = stack[stack.length - 1];
                            current.children.push(node);
                            current = node;
                            lastLevel = level;
                        }}
                        
                        return root;
                    }}
                    
                    try {{
                        // 尝试使用内置转换器
                        if (window.markmap.Transformer) {{
                            const transformer = new window.markmap.Transformer();
                            const {{ root }} = transformer.transform(markdown);
                            const mm = Markmap.create('#markmap', options, root);
                
                            // 添加快捷键
                            document.addEventListener('keydown', e => {{
                                if (e.key === ' ') mm.fit();
                                if (e.key === '+') mm.setZoom(mm.getZoom() * 1.2);
                                if (e.key === '-') mm.setZoom(mm.getZoom() / 1.2);
                                if (/^[1-9]$/.test(e.key)) {{
                                    mm.options.initialExpandLevel = parseInt(e.key);
                                    mm.setData(root);
                                }}
                            }});
                        }} else {{
                            // 回退到简单解析
                            const root = parseMarkdown(markdown);
                            const mm = Markmap.create('#markmap', options, root);
                            
                            // 添加快捷键
                            document.addEventListener('keydown', e => {{
                                if (e.key === ' ') mm.fit();
                                if (e.key === '+') mm.setZoom(mm.getZoom() * 1.2);
                                if (e.key === '-') mm.setZoom(mm.getZoom() / 1.2);
                            }});
                        }}
                    }} catch (err) {{
                        console.error('创建思维导图时出错:', err);
                        document.body.innerHTML = `
                            <div style="margin: 20px; color: red;">
                                <h2>创建思维导图时出错</h2>
                                <p>${{err.message}}</p>
                                <pre>${{markdown}}</pre>
                            </div>
                        `;
                    }}
                }};
            </script>
        </body>
        </html>
        '''

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