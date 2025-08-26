# -*- coding:utf-8 -*-

"""
智能代理管理器
优化2分钟有效期代理的使用效率
"""

import time
import random
import threading
from datetime import datetime, timedelta
from queue import Queue, Empty
from dataclasses import dataclass
from typing import List, Optional

from utils.logger import logger


@dataclass
class ProxyInfo:
    """代理信息类"""
    ip: str
    port: str
    server: str
    area: str
    isp: str
    deadline: str
    created_time: float
    used_count: int = 0
    last_used: float = 0
    is_warming: bool = False
    is_valid: bool = True


class SmartProxyManager:
    """智能代理管理器"""
    
    def __init__(self):
        self.proxy_pool = Queue()
        self.active_proxies = {}  # {server: ProxyInfo}
        self.warming_proxies = set()  # 正在预热的代理
        self.lock = threading.Lock()
        self.max_requests_per_proxy = 8  # 每个代理最多使用8次（2分钟/15秒间隔）
        self.warmup_requests = 3  # 预热请求数量
        
    def add_proxy(self, proxy_data: dict) -> bool:
        """添加代理到池中"""
        try:
            proxy_info = ProxyInfo(
                ip=proxy_data.get('proxy_ip', ''),
                port='',
                server=proxy_data.get('server', ''),
                area=proxy_data.get('area', ''),
                isp=proxy_data.get('isp', ''),
                deadline=proxy_data.get('deadline', ''),
                created_time=time.time()
            )
            
            # 解析server字段获取IP和端口
            if ':' in proxy_info.server:
                proxy_info.ip, proxy_info.port = proxy_info.server.split(':')
            
            with self.lock:
                if proxy_info.server not in self.active_proxies:
                    self.active_proxies[proxy_info.server] = proxy_info
                    self.proxy_pool.put(proxy_info)
                    logger.info(f"添加代理: {proxy_info.server} ({proxy_info.area})")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"添加代理失败: {e}")
            return False
    
    def get_proxy_for_warmup(self) -> Optional[ProxyInfo]:
        """获取用于预热的代理"""
        try:
            with self.lock:
                # 1. 优先寻找未使用的新代理
                for server, proxy in self.active_proxies.items():
                    if (not proxy.is_warming and 
                        proxy.used_count == 0 and 
                        proxy.is_valid and
                        server not in self.warming_proxies):
                        
                        proxy.is_warming = True
                        self.warming_proxies.add(server)
                        logger.info(f"选择代理进行预热: {proxy.server}")
                        return proxy
                
                # 2. 如果没有新代理，寻找正在预热但还没用完的代理
                for server, proxy in self.active_proxies.items():
                    if (proxy.is_warming and 
                        proxy.used_count < self.max_requests_per_proxy and
                        proxy.is_valid):
                        
                        logger.info(f"继续使用预热中的代理: {proxy.server}")
                        return proxy
                
                return None
                
        except Exception as e:
            logger.error(f"获取预热代理失败: {e}")
            return None
    
    def get_proxy_for_crawling(self) -> Optional[ProxyInfo]:
        """获取用于爬取的代理（已预热的）"""
        try:
            with self.lock:
                # 优先使用已预热且使用次数少的代理
                best_proxy = None
                min_usage = float('inf')
                
                for server, proxy in self.active_proxies.items():
                    if (not proxy.is_warming and 
                        proxy.is_valid and
                        proxy.used_count < self.max_requests_per_proxy and
                        proxy.used_count >= self.warmup_requests):  # 已经完成预热
                        
                        if proxy.used_count < min_usage:
                            min_usage = proxy.used_count
                            best_proxy = proxy
                
                if best_proxy:
                    logger.info(f"选择代理进行爬取: {best_proxy.server} (已使用{best_proxy.used_count}次)")
                    return best_proxy
                
                return None
                
        except Exception as e:
            logger.error(f"获取爬取代理失败: {e}")
            return None
    
    def mark_proxy_used(self, server: str, success: bool = True):
        """标记代理使用情况"""
        with self.lock:
            if server in self.active_proxies:
                proxy = self.active_proxies[server]
                proxy.used_count += 1
                proxy.last_used = time.time()
                
                if not success:
                    proxy.is_valid = False
                    logger.warning(f"代理失效: {server}")
                
                # 完成预热
                if proxy.is_warming and proxy.used_count >= self.warmup_requests:
                    proxy.is_warming = False
                    self.warming_proxies.discard(server)
                    logger.info(f"代理预热完成: {server} (已使用{proxy.used_count}次，可开始爬取)")
                
                # 检查是否需要移除（标记为待移除，避免死锁）
                if proxy.used_count >= self.max_requests_per_proxy or not proxy.is_valid:
                    proxy.is_valid = False  # 标记为无效，稍后清理
                    logger.info(f"代理 {server} 已达到最大使用次数或失效，标记为待清理")
    
    def remove_proxy(self, server: str):
        """移除代理"""
        with self.lock:
            if server in self.active_proxies:
                proxy = self.active_proxies[server]
                del self.active_proxies[server]
                self.warming_proxies.discard(server)
                logger.info(f"移除代理: {server} (使用{proxy.used_count}次)")
    
    def cleanup_expired_proxies(self):
        """清理过期和失效代理"""
        current_time = time.time()
        servers_to_remove = []
        
        with self.lock:
            for server, proxy in self.active_proxies.items():
                # 检查需要移除的代理
                should_remove = False
                
                # 1. 超过100秒的过期代理
                if current_time - proxy.created_time > 110:
                    should_remove = True
                    reason = "过期"
                
                # 2. 标记为无效的代理
                elif not proxy.is_valid:
                    should_remove = True
                    reason = "失效"
                
                # 3. 达到最大使用次数的代理
                elif proxy.used_count >= self.max_requests_per_proxy:
                    should_remove = True
                    reason = "达到最大使用次数"
                
                if should_remove:
                    servers_to_remove.append((server, reason))
        
        # 在锁外移除代理
        for server, reason in servers_to_remove:
            self.remove_proxy(server)
            logger.info(f"清理{reason}代理: {server}")
    
    def get_proxy_stats(self) -> dict:
        """获取代理池统计信息"""
        with self.lock:
            total = len(self.active_proxies)
            warming = len(self.warming_proxies)
            ready = sum(1 for p in self.active_proxies.values() 
                       if not p.is_warming and p.is_valid and p.used_count >= self.warmup_requests)
            fresh = sum(1 for p in self.active_proxies.values() 
                       if p.used_count == 0 and not p.is_warming)
            
            return {
                'total': total,
                'warming': warming,
                'ready': ready,
                'fresh': fresh,
                'expired': 0  # 会被cleanup_expired_proxies清理
            }
    
    def estimate_remaining_requests(self) -> int:
        """估算剩余可用请求数"""
        with self.lock:
            remaining = 0
            for proxy in self.active_proxies.values():
                if proxy.is_valid:  # 所有有效代理都计算剩余请求
                    remaining += max(0, self.max_requests_per_proxy - proxy.used_count)
            return remaining
    
    def should_fetch_more_proxies(self) -> bool:
        """判断是否需要获取更多代理"""
        stats = self.get_proxy_stats()
        remaining = self.estimate_remaining_requests()
        
        # 更保守的策略：优先使用现有代理
        # 1. 如果有可用的已预热代理，不需要新代理
        if stats['ready'] > 0:
            return False
        
        # 2. 如果有正在预热的代理，不需要新代理
        if stats['warming'] > 0:
            return False
        
        # 3. 如果有未使用的新代理，不需要新代理
        if stats['fresh'] > 0:
            return False
        
        # 4. 只有在真正没有可用代理时才获取
        return stats['total'] == 0 or remaining == 0
    
    def get_optimal_request_interval(self) -> float:
        """获取最优请求间隔"""
        stats = self.get_proxy_stats()
        
        if stats['ready'] >= 3:
            # 有足够的已预热代理，可以稍微快一点
            return random.uniform(12, 18)
        elif stats['total'] >= 2:
            # 代理数量一般，保持中等速度
            return random.uniform(15, 25)
        else:
            # 代理不足，需要更慢
            return random.uniform(20, 35)
    
    def format_proxy_for_requests(self, proxy_info: ProxyInfo) -> dict:
        """格式化代理用于requests"""
        proxy_url = f"http://{proxy_info.ip}:{proxy_info.port}"
        return {
            "http": proxy_url,
            "https": proxy_url
        }


class ProxyOptimizedStrategy:
    """代理优化策略"""
    
    def __init__(self, proxy_manager: SmartProxyManager):
        self.proxy_manager = proxy_manager
        self.warmup_queue = Queue()
        self.crawl_queue = Queue()
        
    def plan_requests(self, total_requests: int) -> dict:
        """规划请求策略"""
        stats = self.proxy_manager.get_proxy_stats()
        remaining = self.proxy_manager.estimate_remaining_requests()
        
        # 计算需要的代理数量
        proxies_needed = max(1, (total_requests - remaining + 7) // 8)  # 向上取整
        
        # 计算预热策略
        warmup_needed = max(0, proxies_needed - stats['ready'])
        
        return {
            'total_requests': total_requests,
            'current_ready': stats['ready'],
            'proxies_needed': proxies_needed,
            'warmup_needed': warmup_needed,
            'estimated_time': total_requests * 16,  # 假设平均16秒间隔
            'strategy': 'optimal' if remaining >= total_requests else 'need_more_proxies'
        }
    
    def execute_warmup_phase(self, proxy_info: ProxyInfo) -> bool:
        """执行预热阶段"""
        logger.info(f"开始预热代理: {proxy_info.server}")
        
        warmup_urls = [
            "https://www.dianping.com/",
            "https://www.dianping.com/beijing",
            "https://www.dianping.com/beijing/ch10"
        ]
        
        success_count = 0
        
        for i, url in enumerate(warmup_urls):
            try:
                # 这里需要调用实际的请求方法
                # 为了示例，我们模拟成功
                time.sleep(random.uniform(2, 5))  # 模拟请求时间
                
                # 标记使用
                self.proxy_manager.mark_proxy_used(proxy_info.server, success=True)
                success_count += 1
                
                logger.info(f"预热进度: {proxy_info.server} ({i+1}/{len(warmup_urls)})")
                
                # 预热间隔
                if i < len(warmup_urls) - 1:
                    time.sleep(random.uniform(3, 8))
                
            except Exception as e:
                logger.error(f"预热失败: {proxy_info.server} - {e}")
                self.proxy_manager.mark_proxy_used(proxy_info.server, success=False)
                break
        
        success_rate = success_count / len(warmup_urls)
        logger.info(f"预热完成: {proxy_info.server} (成功率: {success_rate:.1%})")
        
        return success_rate > 0.5


# 全局智能代理管理器
smart_proxy_manager = SmartProxyManager()
proxy_strategy = ProxyOptimizedStrategy(smart_proxy_manager)
