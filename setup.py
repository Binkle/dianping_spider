#!/usr/bin/env python
# -*- coding:utf-8 -*-
from setuptools import setup, find_packages

setup(
    name="dianping_spider",
    version="1.0.2",
    description="大众点评爬虫 + 高德地图POI抓取工具",
    packages=find_packages(),
    install_requires=[
        "requests>=2.25.0",
        "pymysql>=1.0.0",
        "lxml>=4.6.0",
    ],
    python_requires=">=3.7",
    entry_points={
        "console_scripts": [
            "amap-crawler=dianping_spider.amap.cli:main",
        ],
    },
)