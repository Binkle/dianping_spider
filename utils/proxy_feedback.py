# -*- coding:utf-8 -*-

"""
代理使用反馈系统
用于跟踪代理使用情况和效果
"""

import threading
from collections import defaultdict
from utils.logger import logger


class ProxyFeedbackSystem:
    """代理反馈系统"""
    
    def __init__(self):
        self.current_proxy = None  # 当前使用的代理信息
        self.proxy_usage = defaultdict(int)  # 代理使用统计
        self.lock = threading.Lock()
    
    def set_current_proxy(self, proxy_server):
        """设置当前使用的代理"""
        with self.lock:
            self.current_proxy = proxy_server
    
    def report_success(self, response=None):
        """报告请求成功"""
        with self.lock:
            if self.current_proxy:
                from utils.smart_proxy_manager import smart_proxy_manager
                
                # 检查响应质量
                success = True
                if response:
                    if 'verify' in response.url:
                        success = False
                        logger.warning(f"代理 {self.current_proxy} 触发验证码")
                    elif response.status_code == 403:
                        success = False
                        logger.warning(f"代理 {self.current_proxy} 被ban (403)")
                    elif response.status_code != 200:
                        success = False
                        logger.warning(f"代理 {self.current_proxy} 状态码异常: {response.status_code}")
                    else:
                        logger.debug(f"代理 {self.current_proxy} 响应正常: {response.status_code}")
                
                # 标记代理使用情况
                smart_proxy_manager.mark_proxy_used(self.current_proxy, success=success)
                
                if success:
                    self.proxy_usage[self.current_proxy] += 1
                    logger.debug(f"代理 {self.current_proxy} 使用成功")
                
                return success
            else:
                # 没有使用代理的情况下，检查响应质量
                if response:
                    if 'verify' in response.url:
                        logger.warning("本地IP触发验证码")
                        return False
                    elif response.status_code == 403:
                        logger.warning("本地IP被ban (403)")
                        return False
                    elif response.status_code != 200:
                        logger.warning(f"本地IP状态码异常: {response.status_code}")
                        return False
                    else:
                        logger.debug(f"本地IP访问正常: {response.status_code}")
                        return True
                return True
    
    def report_failure(self, error=None):
        """报告请求失败"""
        with self.lock:
            if self.current_proxy:
                from utils.smart_proxy_manager import smart_proxy_manager
                smart_proxy_manager.mark_proxy_used(self.current_proxy, success=False)
                logger.warning(f"代理 {self.current_proxy} 请求失败: {error}")
    
    def clear_current_proxy(self):
        """清除当前代理"""
        with self.lock:
            self.current_proxy = None


# 全局代理反馈系统
proxy_feedback = ProxyFeedbackSystem()
