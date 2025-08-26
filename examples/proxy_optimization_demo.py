# -*- coding:utf-8 -*-

"""
代理优化演示
展示如何最大化利用2分钟有效期的代理
"""

import sys
import os
import time
import random

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.smart_proxy_manager import smart_proxy_manager, proxy_strategy
from utils.advanced_anti_detection import advanced_anti_detection
from utils.requests_utils import requests_util
from utils.logger import logger


def demonstrate_proxy_lifecycle():
    """
    演示代理生命周期管理
    """
    print("=== 代理生命周期演示 ===")
    
    # 模拟代理API返回的数据
    mock_proxy_data = {
        'proxy_ip': '123.115.120.2',
        'server': '60.188.78.108:40091',
        'area_code': 110100,
        'area': '北京市市辖区',
        'isp': '联通',
        'deadline': '2025-08-26 00:03:57'
    }
    
    # 1. 添加代理到池中
    print("1. 添加代理到池中...")
    success = smart_proxy_manager.add_proxy(mock_proxy_data)
    print(f"代理添加结果: {'成功' if success else '失败'}")
    
    # 2. 显示代理池状态
    stats = smart_proxy_manager.get_proxy_stats()
    print(f"代理池状态: {stats}")
    
    # 3. 预热阶段
    print("\n2. 代理预热阶段...")
    warmup_proxy = smart_proxy_manager.get_proxy_for_warmup()
    if warmup_proxy:
        print(f"获取预热代理: {warmup_proxy.server}")
        
        # 模拟预热过程
        warmup_urls = [
            "https://www.dianping.com/",
            "https://www.dianping.com/beijing",
            "https://www.dianping.com/beijing/ch10"
        ]
        
        for i, url in enumerate(warmup_urls):
            print(f"预热请求 {i+1}: {url}")
            # 模拟请求成功
            smart_proxy_manager.mark_proxy_used(warmup_proxy.server, success=True)
            time.sleep(1)  # 模拟请求时间
        
        print("预热完成！")
    
    # 4. 爬取阶段
    print("\n3. 爬取阶段...")
    crawl_proxy = smart_proxy_manager.get_proxy_for_crawling()
    if crawl_proxy:
        print(f"获取爬取代理: {crawl_proxy.server} (已使用{crawl_proxy.used_count}次)")
        
        # 模拟爬取过程
        for i in range(5):  # 模拟5次爬取请求
            print(f"爬取请求 {i+1}")
            smart_proxy_manager.mark_proxy_used(crawl_proxy.server, success=True)
            time.sleep(0.5)
        
        print("爬取完成！")
    
    # 5. 显示最终状态
    final_stats = smart_proxy_manager.get_proxy_stats()
    remaining = smart_proxy_manager.estimate_remaining_requests()
    print(f"\n最终代理池状态: {final_stats}")
    print(f"预估剩余请求数: {remaining}")


def demonstrate_optimal_crawling_strategy():
    """
    演示最优爬取策略
    """
    print("\n=== 最优爬取策略演示 ===")
    
    # 1. 制定爬取计划
    total_requests = 20
    plan = proxy_strategy.plan_requests(total_requests)
    
    print("爬取计划:")
    for key, value in plan.items():
        print(f"  {key}: {value}")
    
    # 2. 计算最优请求间隔
    optimal_interval = smart_proxy_manager.get_optimal_request_interval()
    print(f"\n推荐请求间隔: {optimal_interval:.1f} 秒")
    
    # 3. 展示代理利用效率
    print("\n代理利用效率分析:")
    print("- 每个代理有效期: 2分钟 (120秒)")
    print("- 预热请求: 3次")
    print("- 可用爬取请求: 5次")
    print("- 推荐请求间隔: 15秒")
    print("- 理论最大利用率: 8次请求/120秒 = 93.3%")


def demonstrate_real_world_usage():
    """
    演示真实世界的使用场景
    """
    print("\n=== 真实使用场景演示 ===")
    
    # 模拟爬取10个页面的场景
    pages_to_crawl = [
        "https://www.dianping.com/beijing/ch10/d1",
        "https://www.dianping.com/beijing/ch10/d1/p2",
        "https://www.dianping.com/beijing/ch10/d1/p3",
        "https://www.dianping.com/beijing/ch10/d1/p4",
        "https://www.dianping.com/beijing/ch10/d1/p5",
    ]
    
    print(f"计划爬取 {len(pages_to_crawl)} 个页面")
    
    # 检查代理需求
    stats = smart_proxy_manager.get_proxy_stats()
    if stats['total'] == 0:
        print("需要获取代理...")
        # 这里应该调用实际的代理获取API
        print("（实际使用时会调用代理API获取新代理）")
    
    # 执行预热（如果需要）
    if not advanced_anti_detection.visited_pages:
        print("开始会话预热...")
        # warmup_success = advanced_anti_detection.warm_up_session(use_proxy=True)
        # print(f"预热结果: {'成功' if warmup_success else '失败'}")
        print("（演示模式：跳过实际预热）")
    
    # 模拟爬取过程
    for i, url in enumerate(pages_to_crawl):
        print(f"\n爬取进度: {i+1}/{len(pages_to_crawl)}")
        print(f"目标URL: {url}")
        
        # 获取最优间隔
        interval = smart_proxy_manager.get_optimal_request_interval()
        print(f"等待间隔: {interval:.1f}秒")
        
        # 检查是否需要获取更多代理
        if smart_proxy_manager.should_fetch_more_proxies():
            print("⚠️  需要获取更多代理")
        
        # 显示当前代理状态
        current_stats = smart_proxy_manager.get_proxy_stats()
        print(f"当前代理状态: {current_stats}")
        
        # 模拟等待
        time.sleep(min(2, interval))  # 演示时缩短等待时间
    
    print("\n爬取完成！")


def show_best_practices():
    """
    展示最佳实践
    """
    print("\n=== 2分钟代理最佳实践 ===")
    
    practices = [
        "1. 预热策略:",
        "   - 每个新代理先进行3次预热请求",
        "   - 预热路径: 首页 → 城市页 → 分类页",
        "   - 预热间隔: 3-8秒",
        "",
        "2. 使用策略:",
        "   - 每个代理最多使用8次（含预热）",
        "   - 实际爬取请求: 5次",
        "   - 请求间隔: 12-18秒",
        "",
        "3. 池管理策略:",
        "   - 保持至少3个可用代理",
        "   - 提前10秒清理过期代理",
        "   - 动态调整获取频率",
        "",
        "4. 失败处理:",
        "   - 触发验证码立即停用代理",
        "   - 403错误立即停用代理",
        "   - 连接失败重试其他代理",
        "",
        "5. 效率优化:",
        "   - 并行预热多个代理",
        "   - 根据代理数量调整间隔",
        "   - 监控成功率实时调整",
    ]
    
    for practice in practices:
        print(practice)


if __name__ == "__main__":
    print("🚀 代理优化演示程序")
    print("=" * 50)
    
    # 演示代理生命周期
    demonstrate_proxy_lifecycle()
    
    # 演示最优策略
    demonstrate_optimal_crawling_strategy()
    
    # 演示真实使用
    demonstrate_real_world_usage()
    
    # 显示最佳实践
    show_best_practices()
    
    print("\n" + "=" * 50)
    print("演示完成！")
    
    print("\n💡 关键要点:")
    print("1. 每个代理2分钟有效期，最多8次请求")
    print("2. 前3次用于预热，后5次用于实际爬取")
    print("3. 请求间隔12-18秒，确保不触发风控")
    print("4. 提前获取新代理，保持连续性")
    print("5. 监控代理状态，及时处理异常")
