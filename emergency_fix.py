# -*- coding:utf-8 -*-

"""
紧急修复脚本
用于处理被ban的情况，提供恢复策略
"""

import time
import random
import requests
from utils.logger import logger


def check_ip_status():
    """
    检查当前IP状态
    """
    test_urls = [
        "https://www.dianping.com/",
        "https://www.dianping.com/beijing",
        "https://www.dianping.com/beijing/ch10"
    ]
    
    print("=== IP状态检查 ===")
    
    for url in test_urls:
        try:
            print(f"测试 {url}")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if 'verify' in response.url:
                print(f"❌ {url} - 触发验证码")
                print(f"   验证码链接: {response.url}")
            elif response.status_code == 403:
                print(f"❌ {url} - 被ban (403)")
            elif response.status_code == 200:
                print(f"✅ {url} - 正常 (200)")
            else:
                print(f"⚠️  {url} - 异常状态码: {response.status_code}")
            
            # 请求间隔
            time.sleep(3)
            
        except Exception as e:
            print(f"❌ {url} - 请求失败: {e}")


def suggest_recovery_strategy():
    """
    建议恢复策略
    """
    print("\n=== 恢复策略建议 ===")
    print("1. 立即停止所有爬取活动")
    print("2. 等待至少2-4小时再尝试")
    print("3. 更换IP地址（使用代理或切换网络）")
    print("4. 更新Cookie（重新登录获取）")
    print("5. 降低爬取频率：")
    print("   - 每个请求间隔15-30秒")
    print("   - 每3个请求休息1分钟")
    print("   - 每10个请求休息5分钟")
    print("6. 使用更真实的User-Agent和请求头")
    print("7. 实施预热策略：先访问首页，再访问目标页面")


def test_cookie_validity(cookie_string):
    """
    测试Cookie有效性
    """
    if not cookie_string:
        print("❌ 未提供Cookie")
        return False
    
    print("\n=== Cookie有效性测试 ===")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36',
        'Cookie': cookie_string,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
        'Referer': 'https://www.dianping.com/',
    }
    
    try:
        response = requests.get('https://www.dianping.com/beijing', headers=headers, timeout=10)
        
        if 'verify' in response.url:
            print("❌ Cookie触发验证码")
            return False
        elif response.status_code == 403:
            print("❌ Cookie被ban")
            return False
        elif '登录' in response.text or 'login' in response.text.lower():
            print("⚠️  Cookie可能已过期（需要登录）")
            return False
        elif response.status_code == 200:
            print("✅ Cookie有效")
            return True
        else:
            print(f"⚠️  异常状态码: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Cookie测试失败: {e}")
        return False


def emergency_recovery_test():
    """
    紧急恢复测试
    """
    print("=== 紧急恢复测试 ===")
    print("正在进行极慢速度的测试请求...")
    
    # 使用最保守的策略
    test_url = "https://www.dianping.com/"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    
    try:
        print("1. 测试首页访问...")
        response = requests.get(test_url, headers=headers, timeout=15)
        
        if 'verify' in response.url:
            print("❌ 仍然触发验证码，建议：")
            print("   - 等待更长时间（6-12小时）")
            print("   - 更换IP地址")
            print("   - 手动处理验证码")
            return False
        
        if response.status_code != 200:
            print(f"❌ 状态码异常: {response.status_code}")
            return False
        
        print("✅ 首页访问正常")
        
        # 等待更长时间
        wait_time = 30
        print(f"等待 {wait_time} 秒后测试分类页...")
        time.sleep(wait_time)
        
        # 测试分类页
        category_url = "https://www.dianping.com/beijing/ch10"
        response = requests.get(category_url, headers=headers, timeout=15)
        
        if 'verify' in response.url:
            print("❌ 分类页触发验证码")
            return False
        
        if response.status_code != 200:
            print(f"❌ 分类页状态码异常: {response.status_code}")
            return False
        
        print("✅ 分类页访问正常")
        print("🎉 恢复测试成功！可以尝试极慢速度的爬取")
        
        return True
        
    except Exception as e:
        print(f"❌ 恢复测试失败: {e}")
        return False


if __name__ == "__main__":
    print("🚨 大众点评紧急修复工具 🚨")
    print("=" * 50)
    
    # 1. 检查IP状态
    check_ip_status()
    
    # 2. 建议恢复策略
    suggest_recovery_strategy()
    
    # 3. 测试Cookie（如果提供）
    from utils.spider_config import spider_config
    if hasattr(spider_config, 'COOKIE') and spider_config.COOKIE:
        test_cookie_validity(spider_config.COOKIE)
    
    # 4. 询问是否进行恢复测试
    user_input = input("\n是否进行紧急恢复测试？(y/N): ")
    if user_input.lower() == 'y':
        emergency_recovery_test()
    
    print("\n=== 建议的下一步操作 ===")
    print("1. 如果测试失败，请等待至少4小时后重试")
    print("2. 考虑使用代理IP池")
    print("3. 更新config.ini中的requests_times为更保守的值")
    print("4. 启用高级反检测功能")
    print("5. 考虑使用Selenium模拟真实浏览器行为")
    
    print("\n修复工具运行完成。")
