# -*- coding:utf-8 -*-
import json
import os
import heapq
from collections import deque
from typing import List, Dict, Any, Set, Optional, Tuple

from dianping_spider.utils.logger import logger
from .client import AMapClient
from .tiler import Rectangle
from .seen import SeenStore
from .mysql_writer import MySQLWriter


class JsonlWriter:
    def __init__(self, path: str, enabled: bool = True):
        self.path = path
        self.enabled = enabled
        if not self.enabled:
            return
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        if not os.path.exists(self.path):
            with open(self.path, "w", encoding="utf-8"):
                pass

    def write_many(self, records: List[Dict[str, Any]]):
        if not records or not self.enabled:
            return
        with open(self.path, "a", encoding="utf-8") as f:
            for rec in records:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")


class StateStore:
    def __init__(self, path: str):
        self.path = path
        os.makedirs(os.path.dirname(self.path), exist_ok=True)

    def load(self) -> Optional[Dict[str, Any]]:
        if not os.path.exists(self.path):
            return None
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def save(self, state: Dict[str, Any]):
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.path)


class AMapCrawler:
    """
    自适应切分 + 触顶(=200)细分 + 去重(id, 可持久化) + 行政区过滤 + 配额控制 + 优先级队列 + 边抓边入库
    """
    def __init__(
        self,
        key: Optional[str],
        out_path: str = "dianping_spider/files/amap_poi.jsonl",
        state_path: str = "dianping_spider/files/amap_state.json",
        types: str = "050000,110000",
        page_size: int = 25,  # API最大允许值，优化请求效率
        max_pages: int = 8,   # 单次查询最多200条数据（25*8）
        max_requests: int = 5000,
        max_depth: int = 18,
        resume: bool = True,
        use_priority_queue: bool = True,  # 高密度区域优先
        use_kd_split: bool = True,        # KD二分比四叉树更高效
        base_pages: int = 3,              # 低密度区域智能分页
        use_seen_store: bool = True,
        seen_db_path: str = "dianping_spider/files/amap_seen.db",
        allowed_adcodes: Optional[List[str]] = None,
        allowed_cities: Optional[List[str]] = None,
        write_mysql: bool = False,
        mysql_table: str = "amap_poi",
        mysql_batch: int = 50,
        write_jsonl: bool = True,
    ):
        self.client = AMapClient(key=key)
        self.types = types
        self.page_size = page_size
        self.max_pages = max(1, max_pages)
        self.max_requests = max_requests
        self.max_depth = max_depth
        self.use_priority_queue = use_priority_queue
        self.use_kd_split = use_kd_split
        self.base_pages = max(1, base_pages)

        self.writer = JsonlWriter(out_path, enabled=write_jsonl)
        self.state = StateStore(state_path)
        self.requests_used = 0
        self.total_items_saved = 0

        self.seen_ids: Set[str] = set()
        self.seen_store = SeenStore(seen_db_path) if use_seen_store else None

        self.allowed_adcodes = set(allowed_adcodes or [])
        self.allowed_cities = set(allowed_cities or [])

        self.priority_counter = 0
        self.queue = []
        self.simple_queue = deque()

        self.mysql_writer: Optional[MySQLWriter] = MySQLWriter(mysql_table, mysql_batch) if write_mysql else None
        if write_mysql:
            logger.info(f"MySQL写入已启用: 表={mysql_table}, 批次大小={mysql_batch}")
        else:
            logger.info("MySQL写入已禁用")

        if resume:
            st = self.state.load()
            if st:
                self.requests_used = int(st.get("requests_used", 0))
                self.total_items_saved = int(st.get("total_items_saved", 0))
                q = st.get("queue", [])
                if self.use_priority_queue:
                    for item in q:
                        rect = Rectangle(item["min_lng"], item["min_lat"], item["max_lng"], item["max_lat"])
                        depth = int(item.get("depth", 0))
                        priority = float(item.get("priority", 0))
                        self.priority_counter += 1
                        heapq.heappush(self.queue, (priority, self.priority_counter, rect, depth))
                else:
                    for item in q:
                        rect = Rectangle(item["min_lng"], item["min_lat"], item["max_lng"], item["max_lat"])
                        depth = int(item.get("depth", 0))
                        self.simple_queue.append((rect, depth))
                queue_size = len(self.queue) if self.use_priority_queue else len(self.simple_queue)
                logger.info(f"恢复状态: 已用请求={self.requests_used}, 队列剩余={queue_size}, 已保存={self.total_items_saved}")

    def _persist(self):
        if self.use_priority_queue:
            q_dump = [
                {"min_lng": r.min_lng, "min_lat": r.min_lat, "max_lng": r.max_lng, "max_lat": r.max_lat, "depth": d, "priority": p}
                for (p, _, r, d) in self.queue
            ]
        else:
            q_dump = [
                {"min_lng": r.min_lng, "min_lat": r.min_lat, "max_lng": r.max_lng, "max_lat": r.max_lat, "depth": d}
                for (r, d) in self.simple_queue
            ]
        self.state.save({
            "requests_used": self.requests_used,
            "queue": q_dump,
            "total_items_saved": self.total_items_saved,
        })

    def enqueue_root(self, rect: Rectangle):
        if self.use_priority_queue:
            if not self.queue:
                self.priority_counter += 1
                heapq.heappush(self.queue, (0.0, self.priority_counter, rect, 0))
        else:
            if not self.simple_queue:
                self.simple_queue.append((rect, 0))

    def add_seed(self, rect: Rectangle, depth: int = 0, priority: float = -10.0):
        """
        将热门区域矩形以更高优先级加入队列
        priority 越小优先级越高（与密度优先队列一致）
        """
        if self.use_priority_queue:
            self.priority_counter += 1
            heapq.heappush(self.queue, (priority, self.priority_counter, rect, depth))
        else:
            # 非优先队列模式，插入到左侧以尽快处理
            self.simple_queue.appendleft((rect, depth))

    def _budget_ok(self) -> bool:
        return self.requests_used < self.max_requests

    def _normalize_types(self, types_str: str) -> str:
        s = (types_str or "").replace("，", ",").replace(" ", "")
        s = s.replace(",", "|")
        while "||" in s:
            s = s.replace("||", "|")
        return s.strip("|")

    def _fetch_one_page(self, polygon: str, page_num: int) -> List[Dict[str, Any]]:
        if not self._budget_ok():
            return []
        try:
            types_param = self._normalize_types(self.types)
            logger.info(f"正在请求 polygon={polygon[:50]}... types={types_param} page={page_num} page_size={self.page_size}")
            pois, meta = self.client.search_polygon(
                polygon=polygon, types=types_param, page_num=page_num, page_size=self.page_size
            )
            self.requests_used += 1
            if not pois:
                st = str(meta.get("status", ""))
                ic = str(meta.get("infocode", ""))
                info = str(meta.get("info", ""))
                cnt = meta.get("count", None)
                logger.info(f"API返回 0 条POI数据 status={st} infocode={ic} info={info} count={cnt}")
            else:
                logger.info(f"API返回 {len(pois)} 条POI数据")
            return pois
        except Exception as e:
            logger.warning(f"AMap 请求失败 page={page_num}: {e}")
            self.requests_used += 1
            return []

    def _filter_items(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not self.allowed_adcodes and not self.allowed_cities:
            return items
        out = []
        filtered_count = 0
        for it in items:
            adcode = str(it.get("adcode", "")).strip()
            cityname = str(it.get("cityname", "")).strip()
            
            # 同时指定 adcode 和 city 时，满足任一条件即可（或关系）
            ok = False
            if self.allowed_adcodes and adcode in self.allowed_adcodes:
                ok = True
            if self.allowed_cities and cityname in self.allowed_cities:
                ok = True
            # 只指定一种过滤条件时，必须满足该条件
            if self.allowed_adcodes and not self.allowed_cities and adcode not in self.allowed_adcodes:
                ok = False
            if self.allowed_cities and not self.allowed_adcodes and cityname not in self.allowed_cities:
                ok = False
                
            if ok:
                out.append(it)
            else:
                filtered_count += 1
                
        if filtered_count > 0:
            logger.info(f"过滤了 {filtered_count} 条数据，保留 {len(out)} 条")
            if filtered_count > 0 and len(out) == 0:
                logger.warning(f"样例被过滤数据: adcode={adcode}, cityname={cityname}")
                logger.warning(f"允许的adcodes: {self.allowed_adcodes}")
                logger.warning(f"允许的cities: {self.allowed_cities}")
        return out

    def _page_through(self, rect: Rectangle) -> Tuple[bool, List[Dict[str, Any]], float]:
        polygon = rect.to_polygon_param()
        collected: List[Dict[str, Any]] = []
        hit_cap = False
        pages_fetched = 0
        full_pages = 0
        local_max = self.base_pages

        for page in range(1, self.max_pages + 1):
            if not self._budget_ok():
                break
            page_items = self._fetch_one_page(polygon, page)
            pages_fetched += 1
            if not page_items:
                break

            if len(page_items) >= self.page_size:
                full_pages += 1
            collected.extend(page_items)

            if len(page_items) < self.page_size:
                break

            if page == local_max and local_max < self.max_pages and full_pages == local_max:
                local_max = self.max_pages

            if page == self.max_pages and len(page_items) >= self.page_size:
                hit_cap = True
                break

        density_score = 0.0
        if pages_fetched > 0:
            density_score = (full_pages / pages_fetched)
            if full_pages == pages_fetched and pages_fetched >= self.base_pages:
                density_score += 0.5

        area = rect.width() * rect.height()
        area_inv = 1.0 / max(area, 1e-9)
        density_score_unit = density_score * area_inv

        if hit_cap:
            return True, [], density_score_unit

        collected = self._filter_items(collected)
        return False, collected, density_score_unit

    def _dedup(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        out = []
        new_ids = []
        for it in items:
            pid = str(it.get("id", "")).strip()
            if not pid:
                continue
            if pid in self.seen_ids:
                continue
            if self.seen_store and self.seen_store.contains(pid):
                continue
            self.seen_ids.add(pid)
            new_ids.append(pid)
            out.append(it)
        if self.seen_store and new_ids:
            self.seen_store.add_many(new_ids)
        return out

    def _children(self, rect: Rectangle) -> List[Rectangle]:
        return rect.split_kd() if self.use_kd_split else rect.subdivide()

    def _write_outputs(self, items: List[Dict[str, Any]]):
        if not items:
            logger.debug("_write_outputs 收到空项目列表")
            return
        logger.info(f"_write_outputs 处理 {len(items)} 个项目")
        self.writer.write_many(items)
        if self.mysql_writer:
            logger.info(f"调用 mysql_writer.write_many，传入 {len(items)} 个项目")
            self.mysql_writer.write_many(items)
        else:
            logger.debug("mysql_writer 为 None，跳过数据库写入")

    def crawl(self, root_rect: Rectangle):
        self.enqueue_root(root_rect)

        while self._budget_ok():
            if self.use_priority_queue:
                if not self.queue:
                    break
                _, _, rect, depth = heapq.heappop(self.queue)
            else:
                if not self.simple_queue:
                    break
                rect, depth = self.simple_queue.popleft()

            hit_cap, items, density_score_unit = self._page_through(rect)

            if hit_cap and depth < self.max_depth:
                for child in self._children(rect):
                    if child.width() <= 0 or child.height() <= 0:
                        continue
                    if self.use_priority_queue:
                        priority = -density_score_unit
                        self.priority_counter += 1
                        heapq.heappush(self.queue, (priority, self.priority_counter, child, depth + 1))
                    else:
                        self.simple_queue.append((child, depth + 1))
                queue_size = len(self.queue) if self.use_priority_queue else len(self.simple_queue)
                logger.info(f"细分 depth={depth}->{depth+1}, 队列={queue_size}, 已用请求={self.requests_used}")
                self._persist()
                continue

            if items:
                items = self._dedup(items)
                if items:
                    self._write_outputs(items)
                    self.total_items_saved += len(items)
            self._persist()

        if self.mysql_writer:
            self.mysql_writer.close()

        queue_size = len(self.queue) if self.use_priority_queue else len(self.simple_queue)
        logger.info(f"完成/停止: 保存={self.total_items_saved} 条, 已用请求={self.requests_used}, 队列剩余={queue_size}")