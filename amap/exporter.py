# -*- coding:utf-8 -*-
import os
import csv
import json
from typing import Dict, Any, List, Optional

from dianping_spider.utils.logger import logger


class CsvExporter:
    """
    将 JSONL 文件转换为 CSV 格式
    """
    def __init__(self, jsonl_path: str, csv_path: Optional[str] = None):
        self.jsonl_path = jsonl_path
        if csv_path is None:
            base, _ = os.path.splitext(jsonl_path)
            csv_path = f"{base}.csv"
        self.csv_path = csv_path
        
    def export(self, fields: Optional[List[str]] = None):
        """
        导出 CSV
        :param fields: 指定字段列表，如果为 None 则自动从第一条记录推断
        """
        if not os.path.exists(self.jsonl_path):
            logger.error(f"JSONL 文件不存在: {self.jsonl_path}")
            return False
            
        # 读取第一条记录以确定字段
        auto_fields = fields is None
        if auto_fields:
            try:
                with open(self.jsonl_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            record = json.loads(line)
                            fields = list(record.keys())
                            break
            except Exception as e:
                logger.error(f"读取 JSONL 文件失败: {e}")
                return False
                
        if not fields:
            logger.error("无法确定 CSV 字段")
            return False
            
        # 创建 CSV 文件
        try:
            with open(self.csv_path, 'w', encoding='utf-8', newline='') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fields, extrasaction='ignore')
                writer.writeheader()
                
                # 逐行读取 JSONL 并写入 CSV
                with open(self.jsonl_path, 'r', encoding='utf-8') as jsonlfile:
                    for line in jsonlfile:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            record = json.loads(line)
                            writer.writerow(record)
                        except Exception as e:
                            logger.warning(f"解析 JSONL 行失败: {e}")
                            continue
                            
            logger.info(f"CSV 导出成功: {self.csv_path}")
            return True
        except Exception as e:
            logger.error(f"CSV 导出失败: {e}")
            return False


def jsonl_to_csv(jsonl_path: str, csv_path: Optional[str] = None, fields: Optional[List[str]] = None) -> bool:
    """
    便捷函数：将 JSONL 文件转换为 CSV
    """
    exporter = CsvExporter(jsonl_path, csv_path)
    return exporter.export(fields)