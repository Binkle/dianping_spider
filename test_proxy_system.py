# -*- coding:utf-8 -*-

"""
测试代理系统
"""

import sys
import time
from utils.smart_proxy_manager import smart_proxy_manager
from utils.requests_utils import requests_util
from utils.logger import logger

def test_proxy_fetch():
    """测试代理获取"""
    print("=== 测试代理获取 ===")
    
    # 获取代理
    success = requests_util.fetch_new_proxies()
    print(f"代理获取结果: {'成功' if success else '失败'}")
    
    # 显示代理池状态
    stats = smart_proxy_manager.get_proxy_stats()
    print(f"代理池状态: {stats}")
    
    return success

def test_proxy_usage():
    """测试代理使用"""
    print("\n=== 测试代理使用 ===")
    
    # 获取代理
    proxy = requests_util.get_proxy()
    if proxy:
        print(f"获取到代理: {proxy}")
        
        # 测试代理访问
        try:
            import requests
            r = requests.get('https://www.dianping.com/', proxies=proxy, timeout=10)
            print(f"代理访问结果: 状态码 {r.status_code}")
            if 'verify' in r.url:
                print("❌ 触发验证码")
            else:
                print("✅ 访问正常")
            return True
        except Exception as e:
            print(f"代理访问失败: {e}")
            return False
    else:
        print("❌ 未获取到代理")
        return False

def test_warmup():
    """测试预热功能"""
    print("\n=== 测试预热功能 ===")
    
    from utils.advanced_anti_detection import advanced_anti_detection
    
    # 测试预热
    success = advanced_anti_detection.warm_up_session(use_proxy=False)  # 先用本地IP测试
    print(f"预热结果: {'成功' if success else '失败'}")
    
    return success

if __name__ == "__main__":
    print("🧪 代理系统测试")
    print("=" * 50)
    
    # 1. 测试代理获取
    fetch_success = test_proxy_fetch()
    
    # 2. 测试代理使用
    if fetch_success:
        usage_success = test_proxy_usage()
    else:
        print("跳过代理使用测试（获取失败）")
        usage_success = False
    
    # 3. 测试预热功能
    warmup_success = test_warmup()
    
    print("\n" + "=" * 50)
    print("测试结果汇总:")
    print(f"代理获取: {'✅' if fetch_success else '❌'}")
    print(f"代理使用: {'✅' if usage_success else '❌'}")
    print(f"预热功能: {'✅' if warmup_success else '❌'}")
    
    if all([fetch_success, usage_success, warmup_success]):
        print("\n🎉 所有测试通过！")
    else:
        print("\n⚠️  部分测试失败，需要进一步调试")
