#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
AMap POI 抓取工具启动脚本
解决模块导入路径问题
"""
import sys
import os

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 导入并运行 CLI
from dianping_spider.amap.cli import main

if __name__ == "__main__":
    main()