# 大众点评被ban后的恢复指南

## 当前问题分析

根据您的日志信息，出现了以下问题：
```
2025-08-25 21:03:31,008 - WARNING: 搜索页请求被ban，程序终止
```

这表明您的IP/Cookie已经触发了大众点评的反爬虫机制。

## 立即行动方案

### 1. 紧急停止 🛑
- **立即停止所有爬取活动**
- **不要继续尝试访问**
- **等待至少2-4小时**

### 2. 运行诊断工具
```bash
cd dianping_spider
python emergency_fix.py
```

这个工具会帮您：
- 检查当前IP状态
- 测试Cookie有效性
- 提供恢复建议

## 恢复策略

### 策略A：等待恢复（推荐）
1. **等待时间**: 4-12小时
2. **完全停止**: 不要有任何访问
3. **更换环境**: 
   - 重启路由器获取新IP
   - 或使用代理服务

### 策略B：更换资源
1. **更换IP**:
   ```bash
   # 在config.ini中启用代理
   use_proxy = True
   http_extract = True
   http_link = 你的代理API地址
   ```

2. **更新Cookie**:
   - 使用新的浏览器会话
   - 手动登录大众点评
   - 复制新的Cookie到config.ini

3. **降低频率**:
   ```ini
   # 极保守的配置
   requests_times = 1,20;2,40;3,80;5,180
   ```

### 策略C：预热恢复（最安全）
使用新增的高级反检测功能：

1. **启用预热模式**:
   ```python
   from utils.advanced_anti_detection import advanced_anti_detection
   
   # 会话预热
   success = advanced_anti_detection.warm_up_session()
   if success:
       print("预热成功，可以开始爬取")
   ```

2. **使用渐进式访问**:
   - 首页 → 分类页 → 搜索页
   - 每步间隔10-30秒
   - 模拟真实用户行为

## 技术层面的改进

### 1. 请求头优化
```python
headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
    'Cache-Control': 'max-age=0',
}
```

### 2. 访问模式改进
```python
# 错误的方式：直接访问搜索页
url = "http://www.dianping.com/search/keyword/2/0_美食"

# 正确的方式：模拟用户行为
# 1. 访问首页
# 2. 访问城市页面
# 3. 访问分类页面
# 4. 最后访问搜索页面
```

### 3. 时间控制
```python
import time
import random

# 基础延迟
time.sleep(random.uniform(10, 20))

# 长暂停（模拟用户阅读）
if random.random() < 0.2:  # 20%概率
    time.sleep(random.uniform(60, 180))
```

## 配置文件调整

### 极保守配置（推荐）
```ini
[config]
# 极慢的请求频率
requests_times = 1,20;2,40;3,80;5,180

# 启用所有反检测功能
enable_anti_detection = True
simulate_human_behavior = True
min_request_interval = 15
max_request_interval = 30

# 强烈建议使用代理
use_proxy = True
repeat_nub = 3
http_extract = True

# 减少爬取页数进行测试
need_pages = 2
```

### 中等保守配置
```ini
[config]
requests_times = 1,15;3,30;5,60;10,120
min_request_interval = 10
max_request_interval = 20
need_pages = 5
```

## 监控和调试

### 1. 日志监控
关注以下关键信息：
- `INFO: 正在访问搜索页面` - 确认URL正确
- `WARNING: 搜索页请求被ban` - 立即停止
- `verify` - 触发验证码

### 2. 响应检查
```python
def check_response(response):
    if 'verify' in response.url:
        print("触发验证码，停止爬取")
        return False
    
    if response.status_code == 403:
        print("被ban，停止爬取")
        return False
    
    if len(response.text) < 1000:
        print("响应内容异常")
        return False
    
    return True
```

## 长期解决方案

### 1. 代理池
```python
# 使用多个代理IP轮换
proxy_list = [
    "http://proxy1:port",
    "http://proxy2:port",
    "http://proxy3:port"
]
```

### 2. Cookie池
```python
# 使用多个账号的Cookie
cookie_list = [
    "cookie1...",
    "cookie2...",
    "cookie3..."
]
```

### 3. 分布式爬取
- 多台服务器
- 不同时间段
- 不同IP段

## 测试流程

### 恢复测试步骤
1. **等待充分时间**（至少4小时）
2. **运行诊断工具**
   ```bash
   python emergency_fix.py
   ```
3. **小规模测试**
   ```bash
   # 只爬取1页进行测试
   python main.py --normal=1 --pages=1
   ```
4. **监控结果**
   - 成功：逐步增加页数
   - 失败：继续等待或更换资源

### 成功指标
- ✅ 没有触发验证码
- ✅ 状态码为200
- ✅ 返回正常的HTML内容
- ✅ 包含预期的店铺信息

### 失败指标
- ❌ 出现`verify`链接
- ❌ 状态码403
- ❌ 响应内容异常
- ❌ 立即被重定向

## 预防措施

### 1. 请求频率控制
- 永远不要低于10秒间隔
- 使用随机延迟
- 实施长暂停策略

### 2. 行为模拟
- 维护访问历史
- 使用合理的Referer
- 模拟页面停留时间

### 3. 资源轮换
- 定期更换代理
- 更新Cookie
- 变换User-Agent

## 紧急联系

如果所有方法都失败：
1. 考虑使用Selenium + 真实浏览器
2. 寻找其他数据源
3. 联系专业的反爬虫服务

---

**记住**：耐心是关键。宁可慢一点，也不要被永久封禁。
