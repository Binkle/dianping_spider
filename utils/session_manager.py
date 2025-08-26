# -*- coding:utf-8 -*-

"""
会话管理模块，用于模拟真实用户的浏览行为
"""

import time
import random
import requests
from urllib.parse import urlparse, urljoin


class SessionManager:
    """
    会话管理器，维护用户会话状态和行为模拟
    """
    
    def __init__(self):
        self.session = requests.Session()
        self.last_request_time = 0
        self.page_visit_history = []
        self.current_referer = None
        
    def simulate_human_behavior(self):
        """
        模拟人类浏览行为的延迟
        """
        current_time = time.time()
        if self.last_request_time > 0:
            # 计算距离上次请求的时间间隔
            time_since_last = current_time - self.last_request_time
            
            # 如果间隔太短，增加延迟
            if time_since_last < 2:
                additional_delay = random.uniform(2, 5)
                print(f"模拟人类行为延迟: {additional_delay:.1f}秒")
                time.sleep(additional_delay)
        
        self.last_request_time = time.time()
    
    def update_referer(self, url):
        """
        更新Referer，模拟页面跳转
        """
        if self.current_referer:
            self.page_visit_history.append(self.current_referer)
        self.current_referer = url
    
    def get_natural_referer(self, target_url):
        """
        根据目标URL获取合理的Referer
        """
        if not self.current_referer:
            # 首次访问，使用主页作为referer
            return "https://www.dianping.com/"
        
        # 如果是搜索页到详情页的跳转
        if 'shop' in target_url and 'search' in self.current_referer:
            return self.current_referer
        
        # 如果是同域名下的页面跳转
        target_domain = urlparse(target_url).netloc
        current_domain = urlparse(self.current_referer).netloc
        
        if target_domain == current_domain:
            return self.current_referer
        
        # 跨域请求，使用大众点评主页
        return "https://www.dianping.com/"
    
    def simulate_page_loading(self, url):
        """
        模拟页面加载过程，包括资源请求
        """
        # 模拟页面加载时间
        loading_time = random.uniform(1, 3)
        time.sleep(loading_time)
        
        # 更新访问历史
        self.update_referer(url)
    
    def should_trigger_long_pause(self):
        """
        判断是否应该触发长暂停（模拟用户阅读/思考）
        """
        # 访问了一定数量的页面后，增加长暂停的概率
        if len(self.page_visit_history) > 0:
            pause_probability = min(0.3, len(self.page_visit_history) * 0.05)
            return random.random() < pause_probability
        return False
    
    def generate_realistic_headers(self, url, cookie=None):
        """
        生成更真实的请求头
        """
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'sec-ch-ua': '"Not;A=Brand";v="99", "Google Chrome";v="139", "Chromium";v="139"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
            'Cache-Control': 'max-age=0',
        }
        
        # 添加合理的Referer
        referer = self.get_natural_referer(url)
        if referer:
            headers['Referer'] = referer
            # 调整Sec-Fetch-Site
            if urlparse(url).netloc != urlparse(referer).netloc:
                headers['Sec-Fetch-Site'] = 'cross-site'
            else:
                headers['Sec-Fetch-Site'] = 'same-origin'
        
        # 为AJAX请求调整headers
        if any(keyword in url for keyword in ['ajax', 'api', '.json', 'mapi']):
            headers.update({
                'Accept': 'application/json, text/javascript, */*; q=0.01',
                'X-Requested-With': 'XMLHttpRequest',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
            })
        
        # 添加Cookie
        if cookie:
            headers['Cookie'] = cookie
        
        return headers


# 全局会话管理器实例
session_manager = SessionManager()
