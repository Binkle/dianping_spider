# -*- coding:utf-8 -*-
from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class Rectangle:
    """
    GCJ-02 矩形（lng, lat）
    """
    min_lng: float
    min_lat: float
    max_lng: float
    max_lat: float

    def width(self) -> float:
        return max(0.0, self.max_lng - self.min_lng)

    def height(self) -> float:
        return max(0.0, self.max_lat - self.min_lat)

    def area(self) -> float:
        return max(0.0, self.width() * self.height())

    def subdivide(self) -> List["Rectangle"]:
        mid_lng = (self.min_lng + self.max_lng) / 2.0
        mid_lat = (self.min_lat + self.max_lat) / 2.0
        return [
            Rectangle(self.min_lng, self.min_lat, mid_lng,    mid_lat),          # SW
            Rectangle(mid_lng,     self.min_lat, self.max_lng, mid_lat),         # SE
            Rectangle(self.min_lng, mid_lat,     mid_lng,     self.max_lat),     # NW
            Rectangle(mid_lng,     mid_lat,     self.max_lng, self.max_lat),     # NE
        ]

    def split_kd(self) -> List["Rectangle"]:
        """
        KD 二分：沿较长边二分
        """
        if self.width() >= self.height():
            mid_lng = (self.min_lng + self.max_lng) / 2.0
            return [
                Rectangle(self.min_lng, self.min_lat, mid_lng, self.max_lat),
                Rectangle(mid_lng, self.min_lat, self.max_lng, self.max_lat),
            ]
        else:
            mid_lat = (self.min_lat + self.max_lat) / 2.0
            return [
                Rectangle(self.min_lng, self.min_lat, self.max_lng, mid_lat),
                Rectangle(self.min_lng, mid_lat, self.max_lng, self.max_lat),
            ]

    def to_polygon_param(self) -> str:
        """
        AMap polygon 参数要求多边形顶点序列，使用矩形五点闭合：
        "lng1,lat1|lng2,lat1|lng2,lat2|lng1,lat2|lng1,lat1"
        """
        p1 = f"{self.min_lng},{self.min_lat}"
        p2 = f"{self.max_lng},{self.min_lat}"
        p3 = f"{self.max_lng},{self.max_lat}"
        p4 = f"{self.min_lng},{self.max_lat}"
        return "|".join([p1, p2, p3, p4, p1])