# -*- coding:utf-8 -*-
import os
import sqlite3
from typing import Iterable

class SeenStore:
    """
    轻量持久化去重：SQLite 存储已见 id
    """
    def __init__(self, db_path: str = "dianping_spider/files/amap_seen.db"):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self._init_table()
        self._mem = set()  # 内存热缓存，减少频繁 IO

    def _init_table(self):
        cur = self.conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS seen (id TEXT PRIMARY KEY)")
        self.conn.commit()

    def contains(self, pid: str) -> bool:
        if pid in self._mem:
            return True
        cur = self.conn.cursor()
        cur.execute("SELECT 1 FROM seen WHERE id=? LIMIT 1", (pid,))
        row = cur.fetchone()
        return row is not None

    def add_many(self, ids: Iterable[str]):
        ids = [i for i in ids if i]
        if not ids:
            return
        self._mem.update(ids)
        cur = self.conn.cursor()
        cur.executemany("INSERT OR IGNORE INTO seen(id) VALUES(?)", [(i,) for i in ids])
        self.conn.commit()

    def close(self):
        try:
            self.conn.close()
        except:
            pass