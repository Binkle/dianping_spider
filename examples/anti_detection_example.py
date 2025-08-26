# -*- coding:utf-8 -*-

"""
大众点评反风控示例脚本
展示如何使用新的防风控功能
"""

import sys
import os
import time
import random

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.requests_utils import requests_util
from utils.session_manager import session_manager
from utils.param_generator import param_generator
from utils.spider_config import spider_config
from utils.logger import logger


def demo_search_with_anti_detection():
    """
    演示使用反风控功能进行搜索
    """
    print("=== 大众点评反风控示例 ===")
    
    # 1. 基础配置检查
    print("\n1. 检查配置...")
    if not spider_config.COOKIE:
        print("警告: 未配置Cookie，建议配置有效的Cookie")
    
    if spider_config.USE_PROXY:
        print("已启用代理模式")
    else:
        print("未启用代理模式，建议在生产环境中使用代理")
    
    # 2. 模拟正常用户访问流程
    print("\n2. 模拟用户访问流程...")
    
    # 首先访问首页
    homepage_url = "https://www.dianping.com/"
    print(f"访问首页: {homepage_url}")
    
    try:
        # 模拟页面加载
        session_manager.simulate_page_loading(homepage_url)
        
        # 发送首页请求
        r = requests_util.get_requests(homepage_url, request_type='proxy, cookie')
        print(f"首页响应状态: {r.status_code}")
        
        if 'verify' in r.url:
            print("⚠️  首页触发了验证码，请处理后继续")
            return False
        
        # 3. 访问搜索页
        print("\n3. 访问搜索页...")
        search_url = "https://www.dianping.com/beijing/ch10/d1"
        
        # 添加必要参数
        enhanced_search_url = param_generator.add_common_params(search_url)
        print(f"增强后的搜索URL: {enhanced_search_url}")
        
        # 模拟用户在首页停留一段时间
        think_time = random.uniform(3, 8)
        print(f"模拟用户思考时间: {think_time:.1f}秒")
        time.sleep(think_time)
        
        # 访问搜索页
        session_manager.simulate_page_loading(enhanced_search_url)
        r = requests_util.get_requests(enhanced_search_url, request_type='proxy, cookie')
        print(f"搜索页响应状态: {r.status_code}")
        
        if 'verify' in r.url:
            print("⚠️  搜索页触发了验证码，请处理后继续")
            return False
        
        # 4. 解析搜索结果
        print("\n4. 解析搜索结果...")
        if r.status_code == 200:
            # 这里可以添加解析逻辑
            print("✅ 成功获取搜索页面内容")
            
            # 检查是否包含店铺信息
            if 'shop' in r.text and 'dianping' in r.text:
                print("✅ 页面包含预期的店铺信息")
            else:
                print("⚠️  页面内容可能不完整")
        
        # 5. 继续访问下一页（如果需要）
        print("\n5. 访问下一页...")
        next_page_url = "https://www.dianping.com/beijing/ch10/d1/p2"
        
        # 模拟用户浏览当前页面的时间
        browse_time = random.uniform(10, 20)
        print(f"模拟用户浏览时间: {browse_time:.1f}秒")
        time.sleep(browse_time)
        
        enhanced_next_url = param_generator.add_common_params(next_page_url)
        session_manager.simulate_page_loading(enhanced_next_url)
        r = requests_util.get_requests(enhanced_next_url, request_type='proxy, cookie')
        print(f"下一页响应状态: {r.status_code}")
        
        if 'verify' in r.url:
            print("⚠️  下一页触发了验证码")
            return False
        
        print("✅ 成功完成多页面访问示例")
        return True
        
    except Exception as e:
        print(f"❌ 发生错误: {e}")
        return False


def demo_detail_page_access():
    """
    演示访问详情页
    """
    print("\n=== 详情页访问示例 ===")
    
    # 模拟从搜索页跳转到详情页
    detail_url = "https://www.dianping.com/shop/G9B5lBAWimhGRPnh"
    
    # 设置合理的referer
    search_referer = "https://www.dianping.com/beijing/ch10/d1"
    session_manager.update_referer(search_referer)
    
    print(f"访问详情页: {detail_url}")
    print(f"来源页面: {search_referer}")
    
    try:
        # 模拟用户点击链接的延迟
        click_delay = random.uniform(1, 3)
        time.sleep(click_delay)
        
        enhanced_detail_url = param_generator.add_common_params(detail_url)
        session_manager.simulate_page_loading(enhanced_detail_url)
        
        r = requests_util.get_requests(enhanced_detail_url, request_type='proxy, cookie')
        print(f"详情页响应状态: {r.status_code}")
        
        if 'verify' in r.url:
            print("⚠️  详情页触发了验证码")
            return False
        
        if r.status_code == 200:
            print("✅ 成功获取详情页内容")
        
        return True
        
    except Exception as e:
        print(f"❌ 详情页访问失败: {e}")
        return False


def show_anti_detection_tips():
    """
    显示反风控使用技巧
    """
    print("\n=== 反风控使用技巧 ===")
    print("1. 请求间隔:")
    print("   - 基础间隔: 3-8秒")
    print("   - 随机长暂停: 10-30秒 (10%概率)")
    print("   - 渐进式增加间隔时间")
    
    print("\n2. Cookie管理:")
    print("   - 使用真实登录用户的Cookie")
    print("   - 定期更新Cookie")
    print("   - 启用Cookie池分散风险")
    
    print("\n3. 代理使用:")
    print("   - 使用高质量代理")
    print("   - 避免单IP过度使用")
    print("   - 监控代理状态")
    
    print("\n4. 行为模拟:")
    print("   - 维护合理的页面跳转路径")
    print("   - 模拟真实的停留时间")
    print("   - 添加随机性延迟")
    
    print("\n5. 监控和调整:")
    print("   - 实时监控验证码触发率")
    print("   - 根据反馈调整策略")
    print("   - 记录成功的配置组合")


if __name__ == "__main__":
    print("开始大众点评反风控示例演示...")
    
    # 显示使用技巧
    show_anti_detection_tips()
    
    # 执行搜索示例
    search_success = demo_search_with_anti_detection()
    
    if search_success:
        # 如果搜索成功，继续演示详情页访问
        detail_success = demo_detail_page_access()
        
        if detail_success:
            print("\n🎉 所有示例都执行成功！")
            print("✅ 未触发验证码，反风控策略有效")
        else:
            print("\n⚠️  详情页访问遇到问题，建议调整策略")
    else:
        print("\n⚠️  搜索页面访问遇到问题，建议:")
        print("1. 检查Cookie是否有效")
        print("2. 降低请求频率")
        print("3. 使用代理IP")
        print("4. 更新请求参数")
    
    print("\n示例演示结束。")
