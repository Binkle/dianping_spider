# -*- coding:utf-8 -*-

"""
测试单个代理的完整生命周期
"""

import time
from utils.smart_proxy_manager import smart_proxy_manager
from utils.requests_utils import requests_util
from utils.logger import logger

def test_single_proxy_lifecycle():
    """测试单个代理的完整8次使用"""
    print("=== 单个代理生命周期测试 ===")
    
    # 清空代理池
    smart_proxy_manager.active_proxies.clear()
    smart_proxy_manager.warming_proxies.clear()
    
    # 1. 获取一个新代理
    print("1. 获取新代理...")
    success = requests_util.fetch_new_proxies()
    if not success:
        print("❌ 获取代理失败")
        return False
    
    stats = smart_proxy_manager.get_proxy_stats()
    remaining = smart_proxy_manager.estimate_remaining_requests()
    print(f"初始状态: {stats}, 剩余请求: {remaining}")
    
    # 2. 连续使用8次
    print("\n2. 连续使用同一个代理8次...")
    proxy_servers = []
    
    for i in range(8):
        print(f"\n--- 第{i+1}次使用 ---")
        
        # 获取代理
        proxy = requests_util.get_proxy()
        if not proxy:
            print(f"第{i+1}次获取代理失败")
            break
            
        server = requests_util.extract_proxy_server(proxy)
        proxy_servers.append(server)
        print(f"使用代理: {server}")
        
        # 模拟请求并手动标记使用
        try:
            import requests
            r = requests.get('https://www.dianping.com/', proxies=proxy, timeout=5)
            print(f"请求结果: {r.status_code}")
            
            # 手动标记使用成功
            if server:
                smart_proxy_manager.mark_proxy_used(server, success=True)
                
        except Exception as e:
            print(f"请求失败: {e}")
            if server:
                smart_proxy_manager.mark_proxy_used(server, success=False)
        
        # 显示当前状态
        stats = smart_proxy_manager.get_proxy_stats()
        remaining = smart_proxy_manager.estimate_remaining_requests()
        print(f"当前状态: {stats}, 剩余请求: {remaining}")
        
        time.sleep(0.5)  # 短暂间隔
    
    # 3. 分析结果
    print(f"\n3. 使用分析:")
    print(f"总共使用了 {len(set(proxy_servers))} 个不同的代理")
    print(f"代理使用记录: {proxy_servers}")
    
    if len(set(proxy_servers)) == 1:
        print("✅ 成功！单个代理被重复使用")
        return True
    else:
        print("❌ 失败！使用了多个代理")
        return False

if __name__ == "__main__":
    print("🧪 单个代理生命周期测试")
    print("=" * 50)
    
    result = test_single_proxy_lifecycle()
    
    print("\n" + "=" * 50)
    print(f"测试结果: {'✅ 通过' if result else '❌ 失败'}")
    
    if result:
        print("\n🎉 代理重复使用机制正常工作！")
    else:
        print("\n⚠️  需要进一步调试代理重复使用机制")
