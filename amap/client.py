# -*- coding:utf-8 -*-
import os
import time
import json
import random
from typing import Dict, Any, Optional, Tuple, List

import requests

from dianping_spider.utils.logger import logger


RETRYABLE_HTTP = {408, 429, 500, 502, 503, 504}
RETRYABLE_INFO_SUBSTR = ("TOO_FAST", "OVER_LIMIT", "SERVICE_NOT_AVAILABLE")


class AMapClient:
    """
    AMap Webservice v5 newpoisearch 客户端（place/polygon）
    - page_size 1-25；同参最多200条
    - 多KEY轮换 + 指数退避 + 有限重试
    """
    def __init__(
        self,
        key: Optional[str] = None,
        base_url: str = "https://restapi.amap.com/v5/place/polygon",
        timeout: int = 15,
        min_delay: float = 0.12,
        max_delay: float = 0.28,
        max_retries: int = 3,
        backoff_base: float = 0.8,
        backoff_factor: float = 1.8
    ):
        keys_env = key or os.environ.get("AMAP_KEYS") or os.environ.get("AMAP_KEY", "")
        self.keys: List[str] = [k.strip() for k in keys_env.split(",") if k.strip()]
        if not self.keys:
            raise RuntimeError("缺少 AMAP_KEY/AMAP_KEYS 环境变量")
        self.key_idx = 0

        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        self.backoff_factor = backoff_factor

    def _sleep(self):
        time.sleep(random.uniform(self.min_delay, self.max_delay))

    def _cur_key(self) -> str:
        return self.keys[self.key_idx]

    def _rotate_key(self):
        self.key_idx = (self.key_idx + 1) % len(self.keys)
        logger.info(f"切换AMAP KEY -> idx={self.key_idx}")

    def _should_rotate(self, info: str, code: str) -> bool:
        if not info and not code:
            return False
        info = (info or "").upper()
        code = str(code or "")
        # 常见超限/限速
        if "OVER_LIMIT" in info or "TOO_FAST" in info:
            return True
        if code in {"10003", "10004", "10005"}:  # 权限、密钥问题
            return True
        return False

    def search_polygon(
        self, polygon: str, types: str, page_num: int, page_size: int = 25
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        调用 place/polygon
        :return: (pois列表, 原始响应json)
        """
        assert 1 <= page_size <= 25
        attempt = 0
        delay = self.backoff_base

        while True:
            params = {
                "key": self._cur_key(),
                "polygon": polygon,
                "page_size": page_size,
                "page_num": page_num,
                "output": "json",
                "show_fields": "base,business,children,indoor,navi,photos",
            }
            if types and str(types).strip():
                params["types"] = types
            self._sleep()
            try:
                r = requests.get(self.base_url, params=params, timeout=self.timeout)
                if r.status_code != 200:
                    logger.warning(f"AMap HTTP {r.status_code}: {r.text[:200]}")
                    if r.status_code in RETRYABLE_HTTP and attempt < self.max_retries:
                        time.sleep(delay)
                        delay *= self.backoff_factor
                        attempt += 1
                        continue
                    raise RuntimeError(f"AMap HTTP error {r.status_code}")
                data = r.json()
            except Exception as e:
                if attempt < self.max_retries:
                    time.sleep(delay)
                    delay *= self.backoff_factor
                    attempt += 1
                    continue
                raise

            status = str(data.get("status", "0"))
            info = data.get("info", "")
            infocode = str(data.get("infocode", ""))

            if status == "1":
                pois = data.get("pois", []) or []
                return pois, data

            # 业务失败：考虑限速/配额问题 -> 退避且可能换key
            logger.warning(f"AMap业务失败 status={status} infocode={infocode} info={info}")
            rotate = self._should_rotate(info, infocode)
            if rotate:
                self._rotate_key()
            if attempt < self.max_retries:
                time.sleep(delay)
                delay *= self.backoff_factor
                attempt += 1
                continue
            raise RuntimeError(f"AMap biz error: {info} ({infocode})")