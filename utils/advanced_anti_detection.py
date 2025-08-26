# -*- coding:utf-8 -*-

"""
高级反检测模块
实现更复杂的反风控策略
"""

import time
import random
import requests
from urllib.parse import urljoin

from utils.logger import logger
from utils.requests_utils import requests_util
from utils.smart_proxy_manager import smart_proxy_manager, proxy_strategy
from utils.proxy_feedback import proxy_feedback


class AdvancedAntiDetection:
    """
    高级反检测类，实现复杂的反风控策略
    """
    
    def __init__(self):
        self.visited_pages = []
        self.session_start_time = time.time()
        self.last_request_time = 0
        
    def warm_up_session(self, use_proxy=True):
        """
        预热会话，模拟真实用户的访问流程
        支持代理预热
        """
        logger.info(f"开始会话预热... (使用代理: {use_proxy})")
        
        # 如果使用代理，先获取一个代理进行预热
        if use_proxy:
            # 先尝试获取新代理
            from utils.requests_utils import requests_util
            if smart_proxy_manager.get_proxy_stats()['total'] == 0:
                logger.info("代理池为空，尝试获取新代理...")
                requests_util.fetch_new_proxies()
            
            proxy_info = smart_proxy_manager.get_proxy_for_warmup()
            if proxy_info:
                logger.info(f"使用代理进行预热: {proxy_info.server}")
                proxy_feedback.set_current_proxy(proxy_info.server)
            else:
                logger.warning("无可用代理进行预热，使用本地IP")
                use_proxy = False
        else:
            # 不使用代理时，清除代理信息
            proxy_feedback.clear_current_proxy()
        
        request_type = 'proxy, cookie' if use_proxy else 'no proxy, cookie'
        
        try:
            # 预热URL序列 - 模拟真实用户访问路径
            warmup_sequence = [
                ("https://www.dianping.com/", "首页"),
                ("https://www.dianping.com/beijing", "北京主页"),
                ("https://www.dianping.com/beijing/ch10", "美食分类页")
            ]
            
            success_count = 0
            
            for i, (url, description) in enumerate(warmup_sequence):
                logger.info(f"预热步骤 {i+1}/{len(warmup_sequence)}: 访问{description}")
                
                # 模拟用户思考时间
                if i > 0:
                    think_time = random.uniform(3, 8)
                    logger.debug(f"模拟用户思考时间: {think_time:.1f}秒")
                    time.sleep(think_time)
                
                try:
                    r = requests_util.get_requests(url, request_type=request_type)
                    
                    # 报告请求结果
                    if proxy_feedback.report_success(r):
                        success_count += 1
                        self.visited_pages.append(url)
                        logger.info(f"✅ {description} 访问成功")
                        
                        # 模拟用户浏览页面时间
                        browse_time = random.uniform(5, 12)
                        logger.debug(f"模拟浏览{description}: {browse_time:.1f}秒")
                        time.sleep(browse_time)
                    else:
                        logger.warning(f"❌ {description} 访问失败或触发风控")
                        break
                        
                except Exception as e:
                    logger.error(f"预热步骤失败: {description} - {e}")
                    proxy_feedback.report_failure(e)
                    break
            
            success_rate = success_count / len(warmup_sequence)
            logger.info(f"会话预热完成，成功率: {success_rate:.1%}")
            
            # 清除当前代理信息
            proxy_feedback.clear_current_proxy()
            
            return success_rate >= 0.67  # 至少67%成功率才算预热成功
            
        except Exception as e:
            logger.error(f"会话预热失败: {e}")
            proxy_feedback.clear_current_proxy()
            return False
    
    def simulate_search_behavior(self, search_url):
        """
        模拟真实的搜索行为
        """
        logger.info("开始模拟搜索行为...")
        
        try:
            # 1. 如果还没有预热，先进行预热
            if not self.visited_pages:
                if not self.warm_up_session():
                    return None
            
            # 2. 模拟从主页到搜索页的跳转
            time.sleep(random.uniform(2, 5))
            
            # 3. 首先访问美食分类页面
            food_category = "https://www.dianping.com/beijing/ch10"
            logger.info("访问美食分类页面")
            
            r = requests_util.get_requests(food_category, request_type='proxy, cookie')
            if r.status_code != 200 or 'verify' in r.url:
                logger.warning("美食分类页面访问异常")
                return None
            
            # 模拟在分类页面的停留时间
            time.sleep(random.uniform(3, 8))
            
            # 4. 然后访问具体的搜索页面
            logger.info(f"访问搜索页面: {search_url}")
            
            # 添加更真实的延迟
            time.sleep(random.uniform(1, 3))
            
            r = requests_util.get_requests(search_url, request_type='proxy, cookie')
            
            if 'verify' in r.url:
                logger.warning("搜索页面触发验证码")
                return None
            
            if r.status_code == 403:
                logger.warning("搜索页面被ban (403)")
                return None
            
            if r.status_code != 200:
                logger.warning(f"搜索页面访问异常，状态码: {r.status_code}")
                return None
            
            logger.info("搜索行为模拟成功")
            return r
            
        except Exception as e:
            logger.error(f"搜索行为模拟失败: {e}")
            return None
    
    def simulate_page_interaction(self):
        """
        模拟页面交互行为
        """
        # 模拟滚动页面
        scroll_time = random.uniform(0.5, 2)
        time.sleep(scroll_time)
        
        # 模拟鼠标移动和点击
        if random.random() < 0.3:  # 30%概率模拟额外交互
            interaction_time = random.uniform(1, 3)
            time.sleep(interaction_time)
    
    def should_take_break(self):
        """
        判断是否应该休息
        """
        current_time = time.time()
        session_duration = current_time - self.session_start_time
        
        # 会话时间超过30分钟，建议长时间休息
        if session_duration > 1800:
            return True, random.uniform(300, 600)  # 5-10分钟休息
        
        # 会话时间超过15分钟，建议短时间休息
        if session_duration > 900:
            return True, random.uniform(60, 180)  # 1-3分钟休息
        
        return False, 0
    
    def adaptive_delay(self, request_count):
        """
        自适应延迟策略
        """
        base_delay = random.uniform(3, 8)
        
        # 根据请求数量增加延迟
        if request_count > 20:
            base_delay *= 2
        elif request_count > 10:
            base_delay *= 1.5
        
        # 检查是否需要长时间休息
        should_break, break_time = self.should_take_break()
        if should_break:
            logger.info(f"自适应休息 {break_time:.1f} 秒")
            time.sleep(break_time)
            # 重置会话开始时间
            self.session_start_time = time.time()
        else:
            time.sleep(base_delay)
    
    def check_response_quality(self, response):
        """
        检查响应质量，判断是否被风控
        """
        if not response:
            return False, "响应为空"
        
        if 'verify' in response.url:
            return False, "触发验证码"
        
        if response.status_code == 403:
            return False, "被ban (403)"
        
        if response.status_code != 200:
            return False, f"异常状态码: {response.status_code}"
        
        # 检查响应内容
        if len(response.text) < 1000:
            return False, "响应内容过短"
        
        # 检查是否包含预期内容
        if 'dianping' not in response.text.lower():
            return False, "响应内容异常"
        
        return True, "响应正常"
    
    def reset_session(self):
        """
        重置会话状态
        """
        self.visited_pages = []
        self.session_start_time = time.time()
        self.last_request_time = 0
        logger.info("会话状态已重置")


# 全局高级反检测实例
advanced_anti_detection = AdvancedAntiDetection()
