#!/bin/bash
# AMap POI 抓取工具运行脚本

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# 激活虚拟环境
source "$SCRIPT_DIR/.venv/bin/activate"

# 设置 Python 路径并运行
cd "$PROJECT_ROOT"
PYTHONPATH="$PROJECT_ROOT" python -m dianping_spider.amap "$@"