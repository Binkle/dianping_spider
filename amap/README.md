# AMap POI 抓取工具

基于高德地图 newpoisearch API 的 POI 数据抓取工具，支持自适应切分、优先级队列、边抓边入库等功能。

## 功能特性

- **自适应切分**：四叉树/KD二分，触达200上限自动细分
- **优先级队列**：高密度/小面积区域优先抓取
- **行政区过滤**：支持按 adcode/cityname 过滤
- **热门区域优先**：支持种子区域高优先级抓取
- **边抓边入库**：直接写入 MySQL，按字段建列
- **持久化去重**：SQLite 存储已见 ID，支持断点续跑
- **多 Key 轮换**：支持多个 API Key 轮换使用

## 安装依赖

```bash
pip install requests pymysql
```

## 配置

1. 设置高德地图 API Key：
```bash
export AMAP_KEYS="key1,key2,key3"  # 多个 Key 逗号分隔
# 或
export AMAP_KEY="your_single_key"
```

2. 配置 MySQL 数据库（在 utils/spider_config.py 中）：
```python
MYSQL_HOST = 'localhost'
MYSQL_PORT = 3306
MYSQL_USER = 'your_user'
MYSQL_PASSWORD = 'your_password'
MYSQL_DATABASE = 'your_database'
```

## 使用方法

### 方法1：使用启动脚本（推荐）
```bash
cd dianping_spider
python run_amap.py --help
```

### 方法2：设置 PYTHONPATH
```bash
cd /path/to/XTrip/codes
PYTHONPATH=/path/to/XTrip/codes python -m dianping_spider.amap --help
```

### 方法3：使用 Shell 脚本
```bash
cd dianping_spider
./run_amap.sh --help
```

## 使用示例

### 1. 按城市抓取（推荐）
```bash
python run_amap.py --city "110000" --use-kd --priority-queue \
  --write-mysql --mysql-table amap_poi --max-requests 1000
```

### 2. 热门城市优先 + 全国补充
```bash
python run_amap.py --priority-queue --use-kd \
  --city-list "110000,310000,440100,440300,330100" \
  --seed-priority -20 --max-requests 5000 \
  --write-mysql --mysql-table amap_poi
```

### 3. 全国抓取
```bash
python run_amap.py --priority-queue --max-requests 5000 \
  --write-mysql --mysql-table amap_poi
```

### 4. 仅导出文件（不入库）
```bash
python run_amap.py --city "110000" --export-csv \
  --out files/beijing_poi.jsonl --csv-path files/beijing_poi.csv
```

## 参数说明

### 基础参数
- `--types`: POI 类型，默认 "050000,110000"（餐饮+景点）
- `--max-requests`: 请求预算上限，默认 5000
- `--page-size`: 每页条数，默认 25（最大 25）
- `--max-pages`: 同参最多页数，默认 8（最多 200 条）

### 切分策略
- `--use-kd`: 使用 KD 二分（默认四叉树）
- `--priority-queue`: 启用优先级队列
- `--base-pages`: 低密度区域页数，默认 3

### 区域设置
- `--city`: 按城市抓取，如 "北京市" 或 "110000"
- `--bbox`: 自定义矩形范围
- `--city-list`: 热门城市列表（逗号分隔）
- `--seed-file`: 热门城市文件（每行一个）

### 过滤选项
- `--allow-adcode`: 仅保留指定 adcode
- `--allow-city`: 仅保留指定城市名

### 输出选项
- `--write-mysql`: 边抓边入库
- `--mysql-table`: MySQL 表名，默认 "amap_poi"
- `--mysql-batch`: 批量写入大小，默认 1000
- `--export-csv`: 导出 CSV 文件
- `--no-jsonl`: 不写 JSONL 文件

## 输出文件

- **JSONL**: `files/amap_poi.jsonl`（原始数据）
- **CSV**: `files/amap_poi.csv`（可选导出）
- **状态**: `files/amap_state.json`（断点续跑）
- **去重**: `files/amap_seen.db`（SQLite 去重库）

## MySQL 表结构

工具会自动创建表并为每个字段建立独立列：
- 常见字段：id, name, type, typecode, address, location, lon, lat, tel, pname, cityname, adname, adcode 等
- 复杂字段：photos, biz_ext, importance 等使用 JSON 列
- 新字段：运行时自动 ALTER TABLE 添加

## 注意事项

1. **API 限制**：单页最多 25 条，同参最多 200 条
2. **配额管理**：建议设置合理的 max-requests 避免超限
3. **Key 轮换**：多个 Key 可提高稳定性
4. **断点续跑**：程序支持中断后继续运行
5. **去重机制**：基于 POI id 去重，支持跨会话

## 故障排除

### 模块导入错误
确保从正确目录运行，或使用提供的启动脚本。

### MySQL 连接失败
检查 utils/spider_config.py 中的数据库配置。

### API 限制
检查 Key 是否有效，是否超出配额限制。