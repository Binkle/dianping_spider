# AMap POI 数据文件

此目录存放 AMap POI 抓取的数据文件：

- `amap_poi.jsonl`: 抓取的 POI 数据，每行一条 JSON 记录
- `amap_state.json`: 抓取状态文件，用于断点续跑
- `amap_poi.csv`: 可选的 CSV 导出文件

## 使用方法

### 基本抓取（全国范围）

```bash
# 设置高德地图 API Key
export AMAP_KEY="your_amap_key_here"

# 运行抓取（默认抓取餐饮和景点，types=050000,110000）
python -m dianping_spider.amap
```

### 按城市抓取

```bash
# 抓取北京市的餐饮和景点
python -m dianping_spider.amap --city "北京市"
```

### 自定义类型和区域

```bash
# 抓取上海市的购物场所(060000)
python -m dianping_spider.amap --city "上海市" --types "060000"

# 抓取指定矩形区域的医疗机构(090000)
python -m dianping_spider.amap --bbox "116.3,39.9,116.5,40.1" --types "090000"
```

### 高级选项

```bash
# 使用优先级队列（高密度区域优先）
python -m dianping_spider.amap --city "广州市" --priority-queue

# 限制请求数量（配额控制）
python -m dianping_spider.amap --city "深圳市" --max-requests 1000

# 导出为 CSV
python -m dianping_spider.amap --city "杭州市" --export-csv
```

## 数据字段说明

POI 数据包含以下主要字段：

- `id`: POI 唯一标识
- `name`: POI 名称
- `type`: POI 类型编码
- `typecode`: POI 类型编码
- `address`: 地址
- `location`: 坐标（格式：经度,纬度）
- `tel`: 电话
- `pname`: 所在省份名称
- `cityname`: 所在城市名称
- `adname`: 所在区县名称

更多字段详见高德地图 API 文档：https://lbs.amap.com/api/webservice/guide/api-advanced/newpoisearch