#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import webbrowser
from pathlib import Path

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 从markmap_visualizer.py导入类
try:
from src.utils.markmap_visualizer import MarkMapVisualizer
except ImportError:
    print("错误：无法导入MarkMapVisualizer类，请确保已创建src/utils/markmap_visualizer.py文件")
    sys.exit(1)

def test_simple():
    """简单测试MarkMapVisualizer功能"""
    print("开始测试MarkMapVisualizer...")
    
    # 简单的测试markdown内容
    test_md = """# 测试思维导图

## 主要章节
- 第一要点
  - 子要点1
  - 子要点2
- 第二要点

## 次要章节
- 背景信息
- 其他说明
    """
    
    try:
        # 创建可视化器
        visualizer = MarkMapVisualizer()
        
        # 生成可视化
        output_path = visualizer.create_visualization_with_title(test_md, "测试思维导图")
        
        print(f"成功生成思维导图: {output_path}")
        print(f"正在浏览器中打开...")
        
        # 在浏览器中打开
        webbrowser.open(f"file://{os.path.abspath(output_path)}")
        
        return True
    except Exception as e:
        print(f"测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_markmap():
    """
    测试markmap可视化功能
    """
    # 测试markdown内容
    test_md = """# 测试思维导图

## 主要章节
- 第一要点
  - 子要点1
  - 子要点2
- 第二要点

## 次要章节
- 背景信息
- 其他说明
"""

    # 输出目录
    output_dir = Path('output/visualization')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 输出文件路径
    output_file = output_dir / "测试思维导图.html"
    
    # HTML模板
    html_template = '''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>测试思维导图</title>
        <style>
            body { 
                margin: 0;
                padding: 0;
                height: 100vh;
                font-family: "Microsoft YaHei", Arial, sans-serif;
                overflow: hidden;
            }
            #markmap {
                width: 100%;
                height: 100vh;
            }
            .loading {
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(255,255,255,0.9);
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                z-index: 1000;
            }
            .spinner {
                border: 4px solid #f3f3f3;
                border-top: 4px solid #3498db;
                border-radius: 50%;
                width: 40px;
                height: 40px;
                animation: spin 1s linear infinite;
            }
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            .loading-text {
                margin-top: 15px;
                font-size: 16px;
            }
        </style>
    </head>
    <body>
        <div id="markmap"></div>
        <div class="loading">
            <div class="spinner"></div>
            <div class="loading-text">加载思维导图中...</div>
        </div>
        
        <!-- 按顺序加载所需的脚本 -->
        <script src="https://cdn.jsdelivr.net/npm/d3@6.7.0/dist/d3.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/markmap-view@0.2.7/dist/index.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/markmap-lib@0.11.6/dist/browser/index.min.js"></script>
        
        <script>
            // Markdown内容
            const markdown = `{{markdown}}`;
            
            // 主函数
            function renderMarkmap() {
                if (typeof markmap === 'undefined' || typeof markmap.Transformer === 'undefined') {
                    document.body.innerHTML = `
                        <div style="color: red; padding: 20px;">
                            <h2>加载失败</h2>
                            <p>markmap库未正确加载</p>
                        </div>
                    `;
                    return;
                }
                
                try {
                    // 移除加载指示器
                    document.querySelector('.loading').style.display = 'none';
                    
                    // 转换markdown
                    const transformer = new markmap.Transformer();
                    const { root } = transformer.transform(markdown);
                    
                    // 创建思维导图
                    const mm = markmap.Markmap.create('#markmap', {
                        autoFit: true
                    }, root);
                    
                    // 适应窗口
                    setTimeout(() => mm.fit(), 100);
                } catch (err) {
                    console.error('创建思维导图时出错:', err);
                    document.body.innerHTML = `
                        <div style="color: red; padding: 20px;">
                            <h2>创建思维导图时出错</h2>
                            <p>${err.message}</p>
                        </div>
                    `;
                }
            }
            
            // 等待页面加载完成
            window.onload = renderMarkmap;
        </script>
    </body>
    </html>
    '''
    
    # 替换模板中的markdown内容
    html_content = html_template.replace('{{markdown}}', test_md)
    
    # 写入文件
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"思维导图HTML文件已生成: {output_file}")
    
    # 在浏览器中打开
    try:
        webbrowser.open(f"file://{os.path.abspath(output_file)}")
        print("已在浏览器中打开文件")
    except Exception as e:
        print(f"无法自动打开文件，请手动打开: {output_file}")
        print(f"错误信息: {str(e)}")

if __name__ == "__main__":
    success = test_simple()
    if success:
        print("\n测试成功完成!")
    else:
        print("\n测试失败!")

    test_markmap()
