# -*- coding:utf-8 -*-

"""
测试代理计数修复
"""

import time
from utils.smart_proxy_manager import smart_proxy_manager
from utils.requests_utils import requests_util
from utils.proxy_feedback import proxy_feedback
from utils.logger import logger

def test_proxy_counting():
    """测试代理计数是否正确"""
    print("=== 代理计数测试 ===")
    
    # 清空代理池
    smart_proxy_manager.active_proxies.clear()
    smart_proxy_manager.warming_proxies.clear()
    
    # 1. 获取新代理
    print("1. 获取新代理...")
    success = requests_util.fetch_new_proxies()
    if not success:
        print("❌ 获取代理失败")
        return False
    
    stats = smart_proxy_manager.get_proxy_stats()
    print(f"初始状态: {stats}")
    
    # 2. 设置代理并测试计数
    proxy = requests_util.get_proxy()
    if not proxy:
        print("❌ 获取代理失败")
        return False
    
    server = requests_util.extract_proxy_server(proxy)
    print(f"使用代理: {server}")
    
    # 设置当前代理
    proxy_feedback.set_current_proxy(server)
    
    # 3. 模拟3次请求
    print("\n2. 模拟3次请求...")
    for i in range(3):
        print(f"第{i+1}次请求...")
        
        # 模拟请求成功
        proxy_feedback.report_success()
        
        # 显示状态
        stats = smart_proxy_manager.get_proxy_stats()
        print(f"  状态: {stats}")
        
        time.sleep(0.5)
    
    # 4. 检查代理状态
    print("\n3. 检查代理状态...")
    if server in smart_proxy_manager.active_proxies:
        proxy_info = smart_proxy_manager.active_proxies[server]
        print(f"代理 {server}:")
        print(f"  - 使用次数: {proxy_info.used_count}")
        print(f"  - 预热状态: {proxy_info.is_warming}")
        print(f"  - 是否有效: {proxy_info.is_valid}")
        
        if proxy_info.used_count == 3 and not proxy_info.is_warming:
            print("✅ 代理计数正确，预热完成")
            return True
        else:
            print("❌ 代理计数异常")
            return False
    else:
        print("❌ 代理不在池中")
        return False

if __name__ == "__main__":
    print("🧪 代理计数修复测试")
    print("=" * 50)
    
    result = test_proxy_counting()
    
    print("\n" + "=" * 50)
    print(f"测试结果: {'✅ 通过' if result else '❌ 失败'}")
    
    if result:
        print("\n🎉 代理计数修复成功！")
    else:
        print("\n⚠️  仍需进一步调试")
