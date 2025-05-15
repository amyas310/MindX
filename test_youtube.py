#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.append(str(project_root))

# 现在可以正常导入项目模块
from src.config import config
from src.downloaders.youtube import YouTubeDownloader


def main():
    url = "https://www.youtube.com/watch?v=wr_TPRevFE4"

    print("\n=== YouTube下载测试 ===")
    print(f"测试URL: {url}")

    try:
        downloader = YouTubeDownloader()
        result = downloader.download(url)

        print("\n下载结果:")
        print(f"标题: {result['title']}")
        print(f"音频文件: {result['audio']}")
        print("\n✓ 测试成功完成！")

    except Exception as e:
        print(f"\n✗ 错误: {str(e)}")


if __name__ == "__main__":
    # 忽略 SSL 警告
    import warnings

    warnings.filterwarnings('ignore', category=Warning)

    main()