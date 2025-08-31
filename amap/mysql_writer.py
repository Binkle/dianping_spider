# -*- coding:utf-8 -*-
import json
import re
from typing import Any, Dict, List, Tuple, Optional

import pymysql

from dianping_spider.utils.spider_config import spider_config
from dianping_spider.utils.logger import logger


def _is_number(x: Any) -> bool:
    if isinstance(x, (int, float)):
        return True
    if isinstance(x, str):
        try:
            float(x)
            return True
        except Exception:
            return False
    return False


def _infer_type(col: str, val: Any) -> str:
    """
    推断MySQL列类型：
    - 经纬度专列：lon/lat -> DECIMAL(11,6)
    - 数组/对象 -> JSON
    - 纯数字 -> DOUBLE
    - 可能很长的字段 -> TEXT
    - 短文本 -> VARCHAR(512)
    - 长文本 -> TEXT
    """
    if col in ("lon", "lat"):
        return "DECIMAL(11,6)"
    if isinstance(val, (list, dict)):
        return "JSON"
    if _is_number(val):
        return "DOUBLE"
    
    # 可能很长的字段直接使用TEXT
    if col in ["tag", "keytag", "rectag", "opentime_week", "opentime_today", "address", "alias"]:
        return "TEXT"
    
    # 特定字段使用合适的VARCHAR长度
    varchar_lengths = {
        "typecode": 128,
        "pname": 128,
        "cityname": 128,
        "adname": 128,
        "tel": 255,
        "business_area": 255,
        "website": 512
    }
    
    if col in varchar_lengths:
        return f"VARCHAR({varchar_lengths[col]})"
    
    if isinstance(val, str) and len(val) > 256:  # 降低阈值，更早使用TEXT
        return "TEXT"
    return "VARCHAR(512)"


def _to_db_value(v: Any) -> Any:
    if isinstance(v, (list, dict)):
        return json.dumps(v, ensure_ascii=False)
    return v


class MySQLWriter:
    """
    动态列写入器：
    - 自动建表（如不存在）
    - 运行期自动增列（新字段）
    - 批量写入（ON DUPLICATE KEY UPDATE）
    - 自动拆分 location -> lon, lat
    """
    BASE_COLUMNS: Dict[str, str] = {
        "id": "VARCHAR(64)",
        "name": "VARCHAR(255)",
        "type": "VARCHAR(255)",
        "typecode": "VARCHAR(128)",  # 增加长度，可能包含多个类型码
        "address": "TEXT",  # 地址可能很长
        "location": "VARCHAR(64)",
        "lon": "DECIMAL(11,6)",
        "lat": "DECIMAL(11,6)",
        "pname": "VARCHAR(128)",  # 省份名可能很长
        "cityname": "VARCHAR(128)",  # 城市名可能很长
        "adname": "VARCHAR(128)",  # 区县名可能很长
        "adcode": "VARCHAR(16)",  # 增加长度
        "pcode": "VARCHAR(16)",  # 增加长度
        "citycode": "VARCHAR(32)",  # 增加长度
        "gridcode": "VARCHAR(32)",  # 增加长度
        "distance": "VARCHAR(64)",  # 距离描述可能很长
        "parent": "VARCHAR(128)",  # 父级信息可能很长
        # business对象下的字段
        "tel": "VARCHAR(255)",  # 电话可能包含多个号码
        "rating": "VARCHAR(32)",  # 评分可能包含额外信息
        "cost": "VARCHAR(64)",  # 消费信息可能很长
        "business_area": "VARCHAR(255)",  # 商圈信息可能很长
        "opentime_today": "TEXT",  # 营业时间可能很长
        "opentime_week": "TEXT",
        "tag": "TEXT",
        "keytag": "TEXT",
        "rectag": "TEXT",
        # 复杂对象字段
        "photos": "JSON",
        "children": "JSON",
        "indoor": "JSON",
        "navi": "JSON",
        # 其他可能字段
        "alias": "TEXT",  # 别名可能很长
        "website": "VARCHAR(512)",  # 网址可能很长
        "email": "VARCHAR(255)",  # 邮箱可能很长
        "postcode": "VARCHAR(32)",
        "indoor_map": "VARCHAR(64)",
        "entr_location": "VARCHAR(128)",  # 入口位置可能很长
        "exit_location": "VARCHAR(128)",  # 出口位置可能很长
        "navi_poiid": "VARCHAR(128)",  # 导航ID可能很长
        "shopinfo": "JSON",
        "childtype": "VARCHAR(128)",  # 子类型可能很长
        "biz_ext": "JSON",
        "importance": "JSON",
    }

    def __init__(self, table: str = "amap_poi", batch_size: int = 50, create_if_not_exists: bool = True):
        self.table = table
        self.batch_size = batch_size
        logger.info(f"初始化 MySQLWriter: table={table}, batch_size={batch_size}")
        self.conn = pymysql.connect(
            host=spider_config.MYSQL_HOST,
            port=spider_config.MYSQL_PORT,
            user=spider_config.MYSQL_USER,
            password=spider_config.MYSQL_PASSWORD,
            database=spider_config.MYSQL_DATABASE,
            charset="utf8mb4",
            autocommit=False,
        )
        self.cur = self.conn.cursor()
        logger.info(f"MySQL 连接成功: {spider_config.MYSQL_HOST}:{spider_config.MYSQL_PORT}/{spider_config.MYSQL_DATABASE}")
        if create_if_not_exists:
            self._ensure_table()
        self.columns = self._load_columns()  # {col: type}
        self.batch_rows: List[Tuple[List[str], List[Any]]] = []  # [(cols, vals)]
        logger.info(f"MySQLWriter 初始化完成，表 {table} 已准备就绪")

    def _ensure_table(self):
        cols_sql = [f"`{k}` {v}" for k, v in self.BASE_COLUMNS.items()]
        ddl = f"""
        CREATE TABLE IF NOT EXISTS `{self.table}` (
          {", ".join(cols_sql)},
          PRIMARY KEY (`id`),
          KEY idx_typecode (`typecode`),
          KEY idx_adcode (`adcode`),
          KEY idx_city (`cityname`),
          KEY idx_lon_lat (`lon`, `lat`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """
        self.cur.execute(ddl)
        self.conn.commit()
        
        # 如果表已存在，检查并修改可能过短的字段类型
        self._upgrade_existing_columns()
    
    def _upgrade_existing_columns(self):
        """升级现有表的字段类型，确保长文本字段使用合适的类型"""
        try:
            # 需要升级为TEXT的字段
            text_fields = {
                "tag": "TEXT",
                "keytag": "TEXT", 
                "rectag": "TEXT",
                "opentime_week": "TEXT",
                "opentime_today": "TEXT",
                "address": "TEXT",
                "alias": "TEXT"
            }
            
            # 需要升级为更长VARCHAR的字段
            varchar_upgrades = {
                "typecode": "VARCHAR(128)",
                "pname": "VARCHAR(128)",
                "cityname": "VARCHAR(128)",
                "adname": "VARCHAR(128)",
                "adcode": "VARCHAR(16)",
                "pcode": "VARCHAR(16)",
                "citycode": "VARCHAR(32)",
                "gridcode": "VARCHAR(32)",
                "distance": "VARCHAR(64)",
                "parent": "VARCHAR(128)",
                "tel": "VARCHAR(255)",
                "rating": "VARCHAR(32)",
                "cost": "VARCHAR(64)",
                "business_area": "VARCHAR(255)",
                "website": "VARCHAR(512)",
                "entr_location": "VARCHAR(128)",
                "exit_location": "VARCHAR(128)",
                "navi_poiid": "VARCHAR(128)",
                "childtype": "VARCHAR(128)"
            }
            
            # 升级TEXT字段
            for field, new_type in text_fields.items():
                if field in self.columns:
                    current_type = self.columns[field].upper()
                    if "VARCHAR" in current_type:
                        try:
                            self.cur.execute(f"ALTER TABLE `{self.table}` MODIFY COLUMN `{field}` {new_type}")
                            self.conn.commit()
                            self.columns[field] = new_type.upper()
                            logger.info(f"升级字段 `{field}` 为 {new_type}")
                        except Exception as e:
                            logger.warning(f"升级字段 `{field}` 失败: {e}")
            
            # 升级VARCHAR字段长度
            for field, new_type in varchar_upgrades.items():
                if field in self.columns:
                    current_type = self.columns[field].upper()
                    if "VARCHAR" in current_type:
                        # 提取当前VARCHAR长度
                        import re
                        match = re.search(r'VARCHAR\((\d+)\)', current_type)
                        if match:
                            current_length = int(match.group(1))
                            # 提取新长度
                            new_match = re.search(r'VARCHAR\((\d+)\)', new_type)
                            if new_match:
                                new_length = int(new_match.group(1))
                                if new_length > current_length:
                                    try:
                                        self.cur.execute(f"ALTER TABLE `{self.table}` MODIFY COLUMN `{field}` {new_type}")
                                        self.conn.commit()
                                        self.columns[field] = new_type.upper()
                                        logger.info(f"升级字段 `{field}` 为 {new_type}")
                                    except Exception as e:
                                        logger.warning(f"升级字段 `{field}` 失败: {e}")
        except Exception as e:
            logger.warning(f"检查字段升级时出错: {e}")

    def _load_columns(self) -> Dict[str, str]:
        self.cur.execute(f"SHOW COLUMNS FROM `{self.table}`")
        cols = {}
        for field, col_type, *_ in self.cur.fetchall():
            cols[field] = col_type.upper()
        return cols

    def _add_column(self, col: str, col_type: str):
        self.cur.execute(f"ALTER TABLE `{self.table}` ADD COLUMN `{col}` {col_type} NULL")
        self.conn.commit()
        self.columns[col] = col_type.upper()
        logger.info(f"新增列 `{col}` {col_type}")

    def _ensure_columns_for_record(self, rec: Dict[str, Any]):
        # location 派生 lon/lat
        if "location" in rec and ("lon" not in self.columns or "lat" not in self.columns):
            if "lon" not in self.columns:
                self._add_column("lon", "DECIMAL(11,6)")
            if "lat" not in self.columns:
                self._add_column("lat", "DECIMAL(11,6)")

        for k, v in rec.items():
            if k not in self.columns:
                col_type = _infer_type(k, v)
                self._add_column(k, col_type)

    def _parse_lon_lat(self, loc: Optional[str]) -> Tuple[Optional[float], Optional[float]]:
        if not loc or "," not in loc:
            return None, None
        try:
            lng, lat = loc.split(",", 1)
            return float(lng), float(lat)
        except Exception:
            return None, None

    def _flatten_record(self, rec: Dict[str, Any]) -> Dict[str, Any]:
        """
        展开嵌套对象到平级字段
        business.tel -> tel
        business.rating -> rating
        保留复杂对象（如photos, children）为JSON
        """
        flattened = {}
        
        for key, value in rec.items():
            if key == "business" and isinstance(value, dict):
                # 展开business对象到顶级字段
                for sub_key, sub_value in value.items():
                    if sub_value is not None and str(sub_value).strip():
                        flattened[sub_key] = sub_value
            elif key in ["photos", "children", "indoor", "navi"] and value:
                # 复杂对象保留为JSON
                flattened[key] = value
            else:
                # 普通字段直接复制
                flattened[key] = value
                
        return flattened

    def _build_row(self, rec: Dict[str, Any]) -> Tuple[List[str], List[Any]]:
        # 展开嵌套对象
        flattened_rec = self._flatten_record(rec)
        
        # 确保列存在
        self._ensure_columns_for_record(flattened_rec)

        cols: List[str] = list(flattened_rec.keys())
        vals: List[Any] = [_to_db_value(flattened_rec[c]) for c in cols]

        # location -> lon/lat
        if "location" in flattened_rec:
            lon, lat = self._parse_lon_lat(flattened_rec.get("location"))
            if "lon" not in cols:
                cols.append("lon")
                vals.append(lon)
            else:
                vals[cols.index("lon")] = lon
            if "lat" not in cols:
                cols.append("lat")
                vals.append(lat)
            else:
                vals[cols.index("lat")] = lat

        # 确保 id 存在
        if "id" not in cols:
            cols.append("id")
            vals.append(None)

        return cols, vals

    def write_many(self, records: List[Dict[str, Any]]):
        if not records:
            logger.debug("write_many 收到空记录列表")
            return
        logger.info(f"write_many 收到 {len(records)} 条记录")
        for rec in records:
            cols, vals = self._build_row(rec)
            self.batch_rows.append((cols, vals))
            if len(self.batch_rows) >= self.batch_size:
                logger.info(f"批次已满 ({len(self.batch_rows)}/{self.batch_size})，开始写入")
                self._flush()

    def _flush(self):
        if not self.batch_rows:
            return

        # 统一列集合（动态）
        all_cols: List[str] = []
        seen = set()
        for cols, _ in self.batch_rows:
            for c in cols:
                if c not in seen:
                    seen.add(c)
                    all_cols.append(c)

        # 生成 SQL
        cols_sql = ", ".join(f"`{c}`" for c in all_cols)
        placeholders = ", ".join(["%s"] * len(all_cols))
        update_sql = ", ".join(f"`{c}`=VALUES(`{c}`)" for c in all_cols if c != "id")
        sql = f"INSERT INTO `{self.table}` ({cols_sql}) VALUES ({placeholders}) ON DUPLICATE KEY UPDATE {update_sql}"

        # 对齐行数据
        params: List[Tuple[Any, ...]] = []
        for cols, vals in self.batch_rows:
            row_map = {c: v for c, v in zip(cols, vals)}
            params.append(tuple(row_map.get(c) for c in all_cols))

        self.cur.executemany(sql, params)
        self.conn.commit()
        logger.info(f"MySQL 写入 {len(params)} 条")
        self.batch_rows.clear()

    def close(self):
        if hasattr(self, '_closed') and self._closed:
            return
            
        logger.info(f"关闭 MySQLWriter，剩余批次数据: {len(self.batch_rows)}")
        try:
            self._flush()
        finally:
            try:
                if hasattr(self, 'cur') and self.cur:
                    self.cur.close()
                if hasattr(self, 'conn') and self.conn:
                    self.conn.close()
                logger.info("MySQL 连接已关闭")
                self._closed = True
            except Exception as e:
                logger.warning(f"关闭MySQL连接时出错: {e}")
                self._closed = True