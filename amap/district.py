# -*- coding:utf-8 -*-
import os
import json
import time
import random
from typing import Dict, Any, List, Optional, Tuple

import requests

from dianping_spider.utils.logger import logger
from .tiler import Rectangle


class DistrictClient:
    """
    高德地图行政区划查询客户端
    用于获取城市/区县边界，作为抓取的基础单元
    """
    def __init__(self, key: Optional[str] = None, 
                 base_url: str = "https://restapi.amap.com/v3/config/district",
                 timeout: int = 15, min_delay: float = 0.5, max_delay: float = 1.0):
        # 支持 AMAP_KEYS 和 AMAP_KEY 两种环境变量名
        self.key = key or os.environ.get("AMAP_KEYS", "").strip() or os.environ.get("AMAP_KEY", "").strip()
        if not self.key:
            raise RuntimeError("缺少 AMAP_KEYS 或 AMAP_KEY 环境变量")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.min_delay = min_delay
        self.max_delay = max_delay
        
    def _sleep(self):
        time.sleep(random.uniform(self.min_delay, self.max_delay))
        
    def get_district(self, keywords: str, subdistrict: int = 0, extensions: str = "all") -> Dict[str, Any]:
        """
        获取行政区划
        :param keywords: 行政区名称，如"北京市"
        :param subdistrict: 子行政区级数 0-无子区 1-返回下一级行政区 2-返回下两级行政区 3-返回下三级行政区
        :param extensions: base-不返回边界 all-返回边界
        :return: 行政区数据
        """
        params = {
            "key": self.key,
            "keywords": keywords,
            "subdistrict": subdistrict,
            "extensions": extensions,
            "output": "json",
        }
        self._sleep()
        r = requests.get(self.base_url, params=params, timeout=self.timeout)
        if r.status_code != 200:
            logger.warning(f"District API HTTP {r.status_code}: {r.text[:200]}")
            raise RuntimeError(f"District API HTTP error {r.status_code}")
            
        try:
            data = r.json()
        except Exception:
            logger.warning(f"District API 非JSON响应: {r.text[:200]}")
            raise
            
        status = str(data.get("status", "0"))
        info = data.get("info", "")
        if status != "1":
            logger.warning(f"District API 业务失败 status={status} info={info}")
            raise RuntimeError(f"District API biz error: {info}")
            
        return data
        
    def get_district_polygons(self, keywords: str, level: str = "district") -> List[Tuple[str, str, List[Rectangle]]]:
        """
        获取行政区划边界多边形
        :param keywords: 行政区名称，如"北京市"
        :param level: 期望返回的行政级别 country-国家 province-省份 city-城市 district-区县
        :return: [(区域名, 区域编码, [Rectangle边界列表]), ...]
        """
        # 对于区县级别，需要使用subdistrict=2来获取完整的层级结构
        if level == "district":
            subdistrict = 2
        else:
            # 确定子区划级别
            subdistrict = {
                "country": 3,
                "province": 2, 
                "city": 1,
                "district": 0
            }.get(level, 0)
        
        data = self.get_district(keywords, subdistrict, "all")
        districts = data.get("districts", [])
        if not districts:
            return []
            
        results = []
        
        def extract_districts(district_list, target_level):
            """递归提取指定级别的区划"""
            for district in district_list:
                name = district.get("name", "")
                adcode = district.get("adcode", "")
                level_type = district.get("level", "")
                
                if level_type == target_level:
                    # 找到目标级别的区划
                    polygons = self._parse_polygons(district.get("polyline", ""))
                    if polygons:
                        results.append((name, adcode, polygons))
                elif "districts" in district and district["districts"]:
                    # 继续递归查找
                    extract_districts(district["districts"], target_level)
        
        # 从顶级开始递归查找
        extract_districts(districts, level)
                    
        return results
    
    def _parse_polygons(self, polyline: str) -> List[Rectangle]:
        """
        解析多边形边界字符串，转换为矩形列表
        :param polyline: 边界坐标字符串，格式为 "lng1,lat1;lng2,lat2;..."
        :return: 矩形列表
        """
        if not polyline:
            return []
            
        # 多边形可能有多个部分，以 | 分隔
        parts = polyline.split("|")
        rectangles = []
        
        for part in parts:
            if not part.strip():
                continue
                
            # 解析坐标点
            points = []
            for point_str in part.split(";"):
                if not point_str.strip():
                    continue
                try:
                    lng, lat = point_str.split(",")
                    points.append((float(lng), float(lat)))
                except Exception:
                    continue
                    
            if not points:
                continue
                
            # 计算边界矩形
            lngs = [p[0] for p in points]
            lats = [p[1] for p in points]
            
            min_lng = min(lngs)
            max_lng = max(lngs)
            min_lat = min(lats)
            max_lat = max(lats)
            
            # 创建矩形
            rect = Rectangle(min_lng, min_lat, max_lng, max_lat)
            rectangles.append(rect)
            
        return rectangles


def get_city_rectangles(city_name: str) -> List[Tuple[str, str, List[Rectangle]]]:
    """
    便捷函数：获取城市下所有区县的边界矩形
    :param city_name: 城市名称，如"北京市"
    :return: [(区县名, 区县编码, [Rectangle边界列表]), ...]
    """
    client = DistrictClient()
    
    # 首先尝试获取区县级边界
    districts = client.get_district_polygons(city_name, "district")
    
    # 如果区县没有边界数据，使用城市整体边界，但返回区县信息用于过滤
    if not districts:
        # 获取城市整体边界
        city_districts = client.get_district_polygons(city_name, "province")
        if not city_districts:
            return []
        
        # 获取区县列表（用于adcode过滤）
        try:
            data = client.get_district("北京市" if city_name == "110000" else city_name, subdistrict=2, extensions="all")
            districts_data = data.get('districts', [])
            
            # 提取所有区县信息
            county_info = []
            def extract_counties(district_list):
                for district in district_list:
                    level_type = district.get("level", "")
                    if level_type == "district":
                        name = district.get("name", "")
                        adcode = district.get("adcode", "")
                        if name and adcode:
                            county_info.append((name, adcode))
                    elif "districts" in district and district["districts"]:
                        extract_counties(district["districts"])
            
            extract_counties(districts_data)
            
            # 使用城市边界，但返回区县信息
            city_name, city_code, city_rects = city_districts[0]
            result = []
            for county_name, county_code in county_info:
                # 每个区县使用相同的城市边界（后续通过空间分割和adcode过滤来处理）
                result.append((county_name, county_code, city_rects))
            
            return result
            
        except Exception as e:
            # 如果获取区县信息失败，直接返回城市边界
            return city_districts
    
    return districts