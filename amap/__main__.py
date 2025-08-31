# -*- coding:utf-8 -*-
"""
AMap POI 抓取工具入口点
可以直接运行: python -m dianping_spider.amap
"""
import sys
import os

# 确保项目根目录在 Python 路径中
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from dianping_spider.amap.cli import main

if __name__ == "__main__":
    main()