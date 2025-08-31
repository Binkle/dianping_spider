# -*- coding:utf-8 -*-
import argparse
import json
import os
from typing import Any, Dict, List, Tuple

import pymysql

from dianping_spider.utils.logger import logger
from dianping_spider.utils.spider_config import spider_config


DDL = """
CREATE TABLE IF NOT EXISTS amap_poi (
  id         VARCHAR(64) PRIMARY KEY,
  name       VARCHAR(255),
  type       VARCHAR(255),
  typecode   VARCHAR(32),
  address    VARCHAR(512),
  location   VARCHAR(64),
  lon        DECIMAL(11,6),
  lat        DECIMAL(11,6),
  tel        VARCHAR(128),
  pname      VARCHAR(64),
  cityname   VARCHAR(64),
  adname     VARCHAR(64),
  adcode     VARCHAR(12),
  pcode      VARCHAR(12),
  citycode   VARCHAR(16),
  gridcode   VARCHAR(16),
  business_area VARCHAR(128),
  distance   VARCHAR(32),
  photos     JSON NULL,
  indoor_map VARCHAR(32),
  website    VARCHAR(255),
  email      VARCHAR(255),
  postcode   VARCHAR(32),
  alias      VARCHAR(255),
  parent     VARCHAR(64),
  entr_location VARCHAR(64),
  exit_location VARCHAR(64),
  navi_poiid VARCHAR(64),
  tag        VARCHAR(255),
  raw        JSON NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  KEY idx_typecode (typecode),
  KEY idx_adcode (adcode),
  KEY idx_city (cityname),
  KEY idx_lon_lat (lon, lat)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""

INSERT_SQL = """
INSERT INTO amap_poi
(id,name,type,typecode,address,location,lon,lat,tel,pname,cityname,adname,adcode,pcode,citycode,gridcode,business_area,distance,photos,indoor_map,website,email,postcode,alias,parent,entr_location,exit_location,navi_poiid,tag,raw)
VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,CAST(%s AS JSON),%s,%s,%s,%s,%s,%s,%s,%s,%s,CAST(%s AS JSON))
ON DUPLICATE KEY UPDATE
name=VALUES(name), type=VALUES(type), typecode=VALUES(typecode),
address=VALUES(address), location=VALUES(location), lon=VALUES(lon), lat=VALUES(lat),
tel=VALUES(tel), pname=VALUES(pname), cityname=VALUES(cityname), adname=VALUES(adname),
adcode=VALUES(adcode), pcode=VALUES(pcode), citycode=VALUES(citycode), gridcode=VALUES(gridcode),
business_area=VALUES(business_area), distance=VALUES(distance), photos=VALUES(photos),
indoor_map=VALUES(indoor_map), website=VALUES(website), email=VALUES(email),
postcode=VALUES(postcode), alias=VALUES(alias), parent=VALUES(parent),
entr_location=VALUES(entr_location), exit_location=VALUES(exit_location),
navi_poiid=VALUES(navi_poiid), tag=VALUES(tag), raw=VALUES(raw);
"""


def parse_lon_lat(loc: str):
    if not loc or "," not in loc:
        return None, None
    try:
        lng, lat = loc.split(",", 1)
        return float(lng), float(lat)
    except Exception:
        return None, None


def to_json(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False)
    except Exception:
        return "null"


def build_row(rec: Dict[str, Any]) -> Tuple[Any, ...]:
    loc = rec.get("location") or ""
    lon, lat = parse_lon_lat(loc)
    row = (
        rec.get("id"),
        rec.get("name"),
        rec.get("type"),
        rec.get("typecode"),
        rec.get("address"),
        loc,
        lon, lat,
        rec.get("tel"),
        rec.get("pname"),
        rec.get("cityname"),
        rec.get("adname"),
        rec.get("adcode"),
        rec.get("pcode"),
        rec.get("citycode"),
        rec.get("gridcode"),
        rec.get("business_area"),
        rec.get("distance"),
        to_json(rec.get("photos")),
        rec.get("indoor_map"),
        rec.get("website"),
        rec.get("email"),
        rec.get("postcode"),
        rec.get("alias"),
        rec.get("parent"),
        rec.get("entr_location"),
        rec.get("exit_location"),
        rec.get("navi_poiid"),
        rec.get("tag"),
        to_json(rec),  # raw
    )
    return row


def import_jsonl(jsonl_path: str, batch_size: int = 1000):
    if not os.path.exists(jsonl_path):
        logger.error(f"文件不存在: {jsonl_path}")
        return

    conn = pymysql.connect(
        host=spider_config.MYSQL_HOST,
        port=spider_config.MYSQL_PORT,
        user=spider_config.MYSQL_USER,
        password=spider_config.MYSQL_PASSWORD,
        database=spider_config.MYSQL_DATABASE,
        charset="utf8mb4",
        autocommit=False,
    )
    cur = conn.cursor()

    # 建表
    cur.execute(DDL)
    conn.commit()

    cnt = 0
    batch: List[Tuple[Any, ...]] = []
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            batch.append(build_row(rec))
            if len(batch) >= batch_size:
                cur.executemany(INSERT_SQL, batch)
                conn.commit()
                cnt += len(batch)
                batch.clear()
                logger.info(f"已导入 {cnt} 条")

    if batch:
        cur.executemany(INSERT_SQL, batch)
        conn.commit()
        cnt += len(batch)

    cur.close()
    conn.close()
    logger.info(f"导入完成，总计 {cnt} 条")


def main():
    ap = argparse.ArgumentParser(description="导入 AMap JSONL 到 MySQL")
    ap.add_argument("--jsonl", type=str, default="dianping_spider/files/amap_poi.jsonl")
    ap.add_argument("--batch", type=int, default=1000)
    args = ap.parse_args()
    import_jsonl(args.jsonl, args.batch)


if __name__ == "__main__":
    main()