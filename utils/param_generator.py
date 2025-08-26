# -*- coding:utf-8 -*-

"""
参数生成器模块，用于生成符合大众点评要求的请求参数
"""

import time
import json
import hashlib
import random
import string
from urllib.parse import urlencode, parse_qs, urlparse


class ParamGenerator:
    """
    参数生成器，生成大众点评需要的各种参数
    """
    
    def __init__(self):
        self.device_id = self.generate_device_id()
        self.session_id = self.generate_session_id()
        self.request_id = self.generate_request_id()
        
    def generate_device_id(self):
        """
        生成设备ID (WEBDFPID格式)
        """
        # 模拟WEBDFPID格式: 字母数字组合-时间戳-随机字符串
        prefix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=20))
        timestamp = str(int(time.time() * 1000))
        suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=15))
        return f"{prefix}-{timestamp}-{suffix}"
    
    def generate_session_id(self):
        """
        生成会话ID (_lxsdk格式)
        """
        # 格式: 随机字符串-随机字符串-数字-随机字符串-随机字符串
        parts = [
            ''.join(random.choices(string.ascii_lowercase + string.digits, k=13)),
            ''.join(random.choices(string.ascii_lowercase + string.digits, k=17)),
            str(random.randint(10000000, 99999999)),
            ''.join(random.choices(string.ascii_lowercase + string.digits, k=6)),
            ''.join(random.choices(string.ascii_lowercase + string.digits, k=13))
        ]
        return '-'.join(parts)
    
    def generate_request_id(self):
        """
        生成请求ID
        """
        return ''.join(random.choices(string.ascii_lowercase + string.digits, k=12))
    
    def generate_mtgsig(self, url, timestamp=None):
        """
        生成mtgsig参数（简化版本，真实的需要逆向分析）
        """
        if timestamp is None:
            timestamp = int(time.time() * 1000)
        
        # 这是一个简化的实现，真实的mtgsig生成需要更复杂的算法
        base_data = {
            "a1": "1.2",
            "a2": timestamp,
            "a3": self.device_id,
            "a5": self.generate_signature(url, timestamp),
            "a6": self.generate_h5_signature(),
            "a8": hashlib.md5(f"{url}{timestamp}".encode()).hexdigest(),
            "a9": "4.0.2,7,225",
            "a10": "dd",
            "x0": 4,
            "d1": hashlib.md5(f"{timestamp}{self.device_id}".encode()).hexdigest()
        }
        
        return json.dumps(base_data, separators=(',', ':'))
    
    def generate_signature(self, url, timestamp):
        """
        生成签名参数a5
        """
        # 简化的签名生成逻辑
        data = f"{url}{timestamp}{self.device_id}"
        signature = hashlib.sha256(data.encode()).hexdigest()[:64]
        return signature
    
    def generate_h5_signature(self):
        """
        生成H5签名参数a6
        """
        # 简化的H5签名生成
        data = f"h5_{self.session_id}_{int(time.time())}"
        return hashlib.sha256(data.encode()).hexdigest()[:128]
    
    def generate_lxsdk_params(self):
        """
        生成lxsdk相关参数
        """
        timestamp = int(time.time() * 1000)
        return {
            '_lxsdk_cuid': self.session_id,
            '_lxsdk': self.session_id,
            '_lxsdk_s': f"{self.request_id}-{random.randint(100, 999)}-{random.randint(100, 999)}-{random.randint(100, 999)}||{random.randint(100, 999)}"
        }
    
    def add_common_params(self, url, params=None):
        """
        为URL添加通用参数
        """
        if params is None:
            params = {}
        
        # 解析现有URL参数
        parsed = urlparse(url)
        existing_params = parse_qs(parsed.query)
        
        # 添加通用参数 - 修复参数名
        common_params = {
            'yodaReady': ['h5'],  # 确保参数值是列表格式
            'csecplatform': ['4'],
            'csecversion': ['4.0.2'],
        }
        
        # 合并参数，避免重复
        all_params = existing_params.copy()
        for key, value in common_params.items():
            if key not in all_params:
                all_params[key] = value
        
        # 重新构建URL
        if all_params:
            query_string = urlencode(all_params, doseq=True)
            new_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{query_string}"
        else:
            new_url = url
        
        return new_url
    
    def generate_tracking_data(self, event_type='PV', page_path=None):
        """
        生成埋点追踪数据
        """
        timestamp = int(time.time() * 1000)
        
        tracking_data = {
            "ch": "web",
            "sc": "1728*1117",
            "ct": "www",
            "appnm": "dp_pc",
            "cityid": "2",
            "sdk_env": "online",
            "evs": [{
                "nm": event_type,
                "tm": timestamp,
                "nt": 0,
                "isauto": 7,
                "req_id": self.request_id,
                "seq": random.randint(1, 1000),
                "lx_inner_data": {
                    "path": page_path or "https://www.dianping.com/",
                    "isHeadless": 0,
                    "labv": 10006,
                    "cv": "prod",
                    "web": 1,
                    "proxy": 1,
                    "btoa": True,
                    "atob": True,
                    "stime": random.uniform(100, 500),
                    "pvid": f"pvid-{random.randint(1000000, 9999999)}-{random.randint(1000000, 9999999)}",
                    "m_msid": f"mem_{self.request_id}",
                    "m_seq": random.randint(1, 20),
                    "req_type": "get"
                }
            }],
            "sv": "4.24.0",
            "ms": self.request_id,
            "c": "dianping_nova",
            "lxid": self.session_id
        }
        
        return json.dumps([tracking_data], separators=(',', ':'))
    
    def update_request_sequence(self):
        """
        更新请求序列号
        """
        self.request_id = self.generate_request_id()


# 全局参数生成器实例
param_generator = ParamGenerator()
