# -*- coding:utf-8 -*-

"""
测试代理使用效率
"""

import time
from utils.smart_proxy_manager import smart_proxy_manager
from utils.requests_utils import requests_util
from utils.logger import logger

def test_proxy_lifecycle():
    """测试代理完整生命周期"""
    print("=== 代理生命周期测试 ===")
    
    # 1. 获取新代理
    print("1. 获取新代理...")
    success = requests_util.fetch_new_proxies()
    if not success:
        print("❌ 获取代理失败")
        return False
    
    stats = smart_proxy_manager.get_proxy_stats()
    print(f"代理池状态: {stats}")
    
    # 2. 模拟8次使用（3次预热 + 5次爬取）
    print("\n2. 模拟代理使用...")
    for i in range(8):
        proxy = requests_util.get_proxy()
        if proxy:
            server = requests_util.extract_proxy_server(proxy)
            print(f"第{i+1}次使用代理: {server}")
            
            # 模拟请求
            try:
                import requests
                r = requests.get('https://www.dianping.com/', proxies=proxy, timeout=5)
                print(f"  - 请求成功: {r.status_code}")
                
                # 手动标记使用（因为这是测试）
                if server:
                    smart_proxy_manager.mark_proxy_used(server, success=True)
            except Exception as e:
                print(f"  - 请求失败: {e}")
                if server:
                    smart_proxy_manager.mark_proxy_used(server, success=False)
        else:
            print(f"第{i+1}次获取代理失败")
        
        time.sleep(1)  # 短暂间隔
        
        # 显示当前状态
        stats = smart_proxy_manager.get_proxy_stats()
        remaining = smart_proxy_manager.estimate_remaining_requests()
        print(f"  - 代理池状态: {stats}, 剩余请求: {remaining}")
    
    print("\n3. 最终状态:")
    final_stats = smart_proxy_manager.get_proxy_stats()
    print(f"代理池状态: {final_stats}")
    
    return True

def test_proxy_reuse():
    """测试代理重复使用"""
    print("\n=== 代理重复使用测试 ===")
    
    # 获取代理
    requests_util.fetch_new_proxies()
    
    used_proxies = set()
    for i in range(5):
        proxy = requests_util.get_proxy()
        if proxy:
            server = requests_util.extract_proxy_server(proxy)
            used_proxies.add(server)
            print(f"使用代理: {server}")
            
            # 模拟使用
            if server:
                smart_proxy_manager.mark_proxy_used(server, success=True)
        
        time.sleep(0.5)
    
    print(f"总共使用了 {len(used_proxies)} 个不同的代理")
    print(f"代理列表: {list(used_proxies)}")
    
    if len(used_proxies) == 1:
        print("✅ 代理重复使用正常")
        return True
    else:
        print("❌ 代理重复使用异常")
        return False

if __name__ == "__main__":
    print("🧪 代理效率测试")
    print("=" * 50)
    
    # 清空现有代理池
    smart_proxy_manager.active_proxies.clear()
    
    # 测试1：代理生命周期
    lifecycle_result = test_proxy_lifecycle()
    
    # 清空代理池
    smart_proxy_manager.active_proxies.clear()
    
    # 测试2：代理重复使用
    reuse_result = test_proxy_reuse()
    
    print("\n" + "=" * 50)
    print("测试结果:")
    print(f"代理生命周期: {'✅' if lifecycle_result else '❌'}")
    print(f"代理重复使用: {'✅' if reuse_result else '❌'}")
    
    if all([lifecycle_result, reuse_result]):
        print("\n🎉 代理效率优化成功！")
    else:
        print("\n⚠️  仍需进一步优化")
