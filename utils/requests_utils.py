# -*- coding:utf-8 -*-

"""
      ┏┛ ┻━━━━━┛ ┻┓
      ┃　　　　　　 ┃
      ┃　　　━　　　┃
      ┃　┳┛　  ┗┳　┃
      ┃　　　　　　 ┃
      ┃　　　┻　　　┃
      ┃　　　　　　 ┃
      ┗━┓　　　┏━━━┛
        ┃　　　┃   神兽保佑
        ┃　　　┃   代码无BUG！
        ┃　　　┗━━━━━━━━━┓
        ┃CREATE BY SNIPER┣┓
        ┃　　　　         ┏┛
        ┗━┓ ┓ ┏━━━┳ ┓ ┏━┛
          ┃ ┫ ┫   ┃ ┫ ┫
          ┗━┻━┛   ┗━┻━┛

"""

import os
import sys
import time
import json
import requests
from tqdm import tqdm
from faker import Factory

from utils.cache import cache
from utils.config import global_config
from utils.logger import logger
from utils.get_file_map import get_map
from utils.cookie_utils import cookie_cache
from utils.spider_config import spider_config
from utils.smart_proxy_manager import smart_proxy_manager


class RequestsUtils():
    """
    请求工具类，用于完成全部的请求相关的操作，并进行全局防ban sleep
    """

    def __init__(self):
        requests_times = spider_config.REQUESTS_TIMES
        self.cookie = spider_config.COOKIE
        self.ua = spider_config.USER_AGENT
        self.ua_engine = Factory.create()
        if self.ua is None:
            logger.error('user agent 暂时不支持为空')
            sys.exit()

        self.cookie_pool = spider_config.USE_COOKIE_POOL
        if self.cookie_pool is True:
            logger.info('使用cookie池')
            if not os.path.exists('cookies.txt'):
                logger.error('cookies.txt文件不存在')
                sys.exit()

        self.ip_proxy = spider_config.USE_PROXY
        if self.ip_proxy:
            self.proxy_pool = []

        try:
            self.stop_times = self.parse_stop_time(requests_times)
        except:
            logger.error('配置文件requests_times解析错误，检查输入（必须英文标点）')
            sys.exit()
        self.global_time = 0

    def create_dir(self, file_name):
        """
        创建文件夹
        :param file_name:
        :return:
        """
        if os.path.exists(file_name):
            return
        else:
            os.mkdir(file_name)

    def parse_stop_time(self, requests_times):
        """
        解析暂停时间
        :param requests_times:
        :return:
        """
        each_stop = requests_times.split(';')
        stop_time = []
        for i in range(len(each_stop) - 1, -1, -1):
            stop_time.append(each_stop[i].split(','))
        return stop_time

    def get_requests(self, url, request_type):
        """
        获取请求
        :param url:
        :return:
        """
        assert request_type in ['no header', 'no proxy, cookie', 'no proxy, no cookie', 'proxy, no cookie',
                                'proxy, cookie']

        # 不需要请求头的请求不计入统计（比如字体文件下载）
        if request_type == 'no header':
            r = requests.get(url=url)
            return r

        # 所有本地ip的请求都进入全局监控，no header由于只用于字体文件下载，不计入监控
        if 'no proxy' in request_type:
            self.freeze_time()

            if request_type == 'no proxy, no cookie':
                r = requests.get(url, headers=self.get_header(cookie=None, need_cookie=False, url=url))

            if request_type == 'no proxy, cookie':
                cur_cookie = self.get_cookie(url)
                r = requests.get(url, headers=self.get_header(cookie=cur_cookie, need_cookie=True, url=url))

            return self.handle_verify(r=r, url=url, request_type=request_type)

        """
        下面两个虽然标记使用代理，但是依然判断。
        使用这种标记的意味着这些请求可以由代理完成，但是理所应当可以不用代理。
        当然，建议使用代理。
        """
        if request_type == 'proxy, no cookie':
            if self.ip_proxy:
                # 增加代理重试机制
                max_retries = 3
                current_proxy_server = None
                for retry in range(max_retries):
                    try:
                        proxy = self.get_proxy()
                        if proxy is None:
                            logger.error('无法获取有效代理')
                            # 如果没有代理，尝试不使用代理
                            r = requests.get(url, headers=self.get_header(None, False, url=url))
                            break
                        
                        # 记录当前使用的代理
                        current_proxy_server = self.extract_proxy_server(proxy)
                        
                        r = requests.get(url, headers=self.get_header(None, False, url=url), proxies=proxy, timeout=10)
                        
                        # 请求成功，标记代理使用（避免重复计数）
                        if current_proxy_server:
                            # 这里不调用mark_proxy_used，让proxy_feedback统一处理
                            pass
                        
                        break
                    except (requests.exceptions.ProxyError, requests.exceptions.ConnectTimeout, requests.exceptions.ReadTimeout) as e:
                        logger.warning(f'代理请求失败 (重试 {retry + 1}/{max_retries}): {e}')
                        if retry == max_retries - 1:
                            # 最后一次重试失败，尝试不使用代理
                            logger.warning('代理重试失败，尝试不使用代理')
                            r = requests.get(url, headers=self.get_header(None, False))
                        else:
                            # 清除失效的代理，获取新代理
                            if hasattr(self, 'proxy_pool') and len(self.proxy_pool) > 0:
                                self.proxy_pool.pop(0)
                            time.sleep(1)  # 短暂等待后重试
                    except Exception as e:
                        logger.error(f'代理请求出现未知错误: {e}')
                        r = requests.get(url, headers=self.get_header(None, False))
                        break
            else:
                r = requests.get(url, headers=self.get_header(None, False))
            return self.handle_verify(r, url, request_type)

        if request_type == 'proxy, cookie':
            # 对于携带cookie的请求，依然计入全局监控
            self.freeze_time()

            cur_cookie = self.get_cookie(url)
            header = self.get_header(cookie=cur_cookie, need_cookie=True)

            if self.ip_proxy:
                # 增加代理重试机制
                max_retries = 3
                current_proxy_server = None
                for retry in range(max_retries):
                    try:
                        proxy = self.get_proxy()
                        if proxy is None:
                            logger.error('无法获取有效代理')
                            # 如果没有代理，尝试不使用代理
                            r = requests.get(url, headers=header)
                            break
                        
                        # 记录当前使用的代理
                        current_proxy_server = self.extract_proxy_server(proxy)
                        
                        r = requests.get(url, headers=header, proxies=proxy, timeout=10)
                        
                        # 请求成功，标记代理使用（避免重复计数）
                        if current_proxy_server:
                            # 这里不调用mark_proxy_used，让proxy_feedback统一处理
                            pass
                        
                        break
                    except (requests.exceptions.ProxyError, requests.exceptions.ConnectTimeout, requests.exceptions.ReadTimeout) as e:
                        logger.warning(f'代理请求失败 (重试 {retry + 1}/{max_retries}): {e}')
                        if retry == max_retries - 1:
                            # 最后一次重试失败，尝试不使用代理
                            logger.warning('代理重试失败，尝试不使用代理')
                            r = requests.get(url, headers=header)
                        else:
                            # 清除失效的代理，获取新代理
                            if hasattr(self, 'proxy_pool') and len(self.proxy_pool) > 0:
                                self.proxy_pool.pop(0)
                            time.sleep(1)  # 短暂等待后重试
                    except Exception as e:
                        logger.error(f'代理请求出现未知错误: {e}')
                        r = requests.get(url, headers=header)
                        break
            else:
                r = requests.get(url, headers=header)

            # 对于cookie池的使用，反馈cookie池状态
            if spider_config.USE_COOKIE_POOL and r.status_code != 200:
                if cur_cookie is not None:
                    cookie_cache.change_state(cur_cookie, self.judge_request_type(url))
                    #  失效之后重复调用本方法直至200
                    return self.get_requests(url, request_type)
            else:
                return self.handle_verify(r, url, request_type)
            return self.handle_verify(r, url, request_type)
        # 其他
        raise AttributeError

    def freeze_time(self):
        """
        时间暂停术！增强随机性和人性化间隔
        @return:
        """
        import random
        
        self.global_time += 1
        
        # 每次请求都添加基础随机延迟，模拟人类行为
        base_delay = random.uniform(1.5, 4.0)  # 1.5-4秒随机延迟
        time.sleep(base_delay)
        
        if self.global_time != 1:
            for each_stop_time in self.stop_times:
                if self.global_time % int(each_stop_time[0]) == 0:
                    # 增加更大的随机性
                    extra_wait = random.randint(0, int(each_stop_time[1]) // 3)
                    total_wait = int(each_stop_time[1]) + extra_wait
                    
                    for i in tqdm(range(total_wait), desc='全局等待'):
                        # 更自然的随机间隔
                        sleep_time = random.uniform(0.8, 1.5)
                        time.sleep(sleep_time)
                    break
        
        # 随机性长暂停，模拟用户思考时间
        if random.random() < 0.1:  # 10%概率触发长暂停
            long_pause = random.uniform(10, 30)
            print(f"模拟用户思考时间，暂停 {long_pause:.1f} 秒")
            time.sleep(long_pause)

    def handle_verify(self, r, url, request_type):
        # 这里只做验证码处理，不做其他判断（例如403）
        # 原因是很多地方需要不同的处理方法，全部移到这里基于现有架构代价有点大
        if 'verify' in r.url:
            """
            不管是使用真实ip还是真实cookie，都对验证码进行处理
            这里有一个问题，就是cookie池到底处不处理验证码，如果处理，
            一定程度上丧失了cookie池的意义，如果不处理，失效的太快。
            暂时处理
            """
            if request_type != 'proxy, no cookie' or not spider_config.USE_PROXY:
                print('处理验证码，按任意键回车后继续', r.url)
                input()
            else:
                print('verify')
            return self.get_requests(url, request_type)
        else:
            return r

    def get_retry_time(self):
        """
        获取ip重试次数
        @return:
        """
        # 这里处理解决请求会异常的问题,允许恰巧当前ip出问题，多试一条
        if spider_config.REPEAT_NUMBER == 0:
            retry_time = 5
        else:
            retry_time = spider_config.REPEAT_NUMBER + 1
        return retry_time

    def get_request_for_interface(self, url):
        """
        专属于接口的请求方法，可以保证返回的都是“正确”的
        @param url:
        @return:
        """
        retry_time = self.get_retry_time()
        while True:
            retry_time -= 1
            r = requests_util.get_requests(url, request_type='proxy, cookie')
            try:
                # request handle v2
                r_json = json.loads(r.text)
                if r_json['code'] == 406:
                    # 处理代理模式冷启动时，首条需要验证
                    # （虽然我也不知道为什么首条要验证，本质上切换ip都是首条。但是这样做有效）
                    if cache.is_cold_start is True:
                        print('处理验证码,按任意键回车继续:', r_json['customData']['verifyPageUrl'])
                        input()
                        r = requests_util.get_requests(url, request_type='proxy, cookie')
                        cache.is_cold_start = False
                # 前置验证码过滤
                if r_json['code'] == 200:
                    break
            except:
                pass
            if retry_time <= 0:
                logger.warning('替换tsv和uuid，或者代理质量较低')
                exit()
        return r

    def get_cookie(self, url):
        """
        获取cookie
        @return:
        """
        if spider_config.USE_COOKIE_POOL:
            while True:
                cur_cookie = cookie_cache.get_cookie(mission_type=self.judge_request_type(url))
                if cur_cookie is not None:
                    break
                logger.info('所有cookie均已失效，替换（替换后等待一段时间会自动继续）或等待解封')
                time.sleep(60)
        else:
            cur_cookie = self.cookie
        return cur_cookie

    def judge_request_type(self, url):
        """
        判断请求类型，由于cookie池是分开维护的，搜索、详情、评论也不是一起被ban的，
        需要对每个cookie的每个页面进行分类
        @param url:
        @return:
        """
        if 'shop' in url:
            return 'detail'
        elif 'review' in url:
            return 'review'
        else:
            return 'search'

    def get_header(self, cookie, need_cookie=True, url=None):
        """
        获取请求头，增强反检测能力
        :return:
        """
        if self.ua is not None:
            ua = self.ua
        else:
            ua = self.ua_engine.user_agent()

        # cookie选择
        if cookie is None:
            cookie = self.cookie

        # 基础请求头
        header = {
            'User-Agent': ua,
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

        # 根据URL类型调整请求头
        if url:
            if 'ajax' in url or 'api' in url or '.json' in url:
                header.update({
                    'Accept': 'application/json, text/javascript, */*; q=0.01',
                    'X-Requested-With': 'XMLHttpRequest',
                    'Sec-Fetch-Dest': 'empty',
                    'Sec-Fetch-Mode': 'cors',
                    'Sec-Fetch-Site': 'same-origin',
                })
                # 为API请求添加Referer
                if 'dianping.com' in url:
                    header['Referer'] = 'https://www.dianping.com/'
            
            # 为跨域请求调整
            if 'meituan.net' in url or 'meituan.com' in url:
                header.update({
                    'Origin': 'https://www.dianping.com',
                    'Referer': 'https://www.dianping.com/',
                    'Sec-Fetch-Site': 'cross-site',
                })

        if need_cookie and cookie:
            header['Cookie'] = cookie

        return header

    def get_proxy(self):
        """
        获取代理 - 集成智能代理管理
        """
        # 清理过期代理
        smart_proxy_manager.cleanup_expired_proxies()
        
        # 优先获取用于爬取的代理（已预热的）
        proxy_info = smart_proxy_manager.get_proxy_for_crawling()
        if proxy_info:
            proxies = smart_proxy_manager.format_proxy_for_requests(proxy_info)
            logger.info(f'使用已预热代理: {proxy_info.server} (第{proxy_info.used_count + 1}次使用)')
            return proxies
        
        # 检查是否需要获取更多代理
        if smart_proxy_manager.should_fetch_more_proxies():
            logger.info("需要获取新代理")
            if self.fetch_new_proxies():
                # 获取新代理后，先尝试获取预热代理
                proxy_info = smart_proxy_manager.get_proxy_for_warmup()
                if proxy_info:
                    proxies = smart_proxy_manager.format_proxy_for_requests(proxy_info)
                    logger.info(f'使用新代理(需预热): {proxy_info.server}')
                    return proxies
        
        # 如果还有未预热的代理，使用它们
        proxy_info = smart_proxy_manager.get_proxy_for_warmup()
        if proxy_info:
            proxies = smart_proxy_manager.format_proxy_for_requests(proxy_info)
            logger.info(f'使用未预热代理: {proxy_info.server}')
            return proxies
        
        logger.error('无可用代理')
        return None
    
    def extract_proxy_server(self, proxy_dict):
        """从代理字典中提取服务器地址"""
        if proxy_dict and 'http' in proxy_dict:
            # proxy_dict格式: {'http': 'http://ip:port', 'https': 'http://ip:port'}
            proxy_url = proxy_dict['http']
            if proxy_url.startswith('http://'):
                return proxy_url[7:]  # 去掉 'http://' 前缀
        return None
    
    def fetch_new_proxies(self):
        """获取新代理"""
        if not spider_config.HTTP_EXTRACT:
            return False
            
        proxy_url = spider_config.HTTP_LINK
        if not proxy_url:
            logger.error('未配置代理API地址')
            return False
        
        try:
            r = requests.get(proxy_url, timeout=10)
            r_json = r.json()
            
            if 'data' in r_json and r_json['data']:
                added_count = 0
                for proxy_data in r_json['data']:
                    if smart_proxy_manager.add_proxy(proxy_data):
                        added_count += 1
                
                logger.info(f'成功添加 {added_count} 个新代理')
                return added_count > 0
            else:
                logger.error(f'代理API返回格式错误: {r_json}')
                return False
                
        except Exception as e:
            logger.error(f'获取代理失败: {e}')
            return False

    def test_proxy(self, ip, port, timeout=5):
        """
        测试代理是否可用
        @param ip: 代理IP
        @param port: 代理端口
        @param timeout: 超时时间
        @return: 是否可用
        """
        # 增加重试机制
        max_retries = 2
        for retry in range(max_retries):
            try:
                proxy = self.http_proxy_utils(ip, port)
                test_url = "http://httpbin.org/ip"
                response = requests.get(test_url, proxies=proxy, timeout=timeout)
                if response.status_code == 200:
                    logger.debug(f'代理 {ip}:{port} 测试成功')
                    return True
            except requests.exceptions.ProxyError as e:
                logger.debug(f'代理 {ip}:{port} 代理错误 (重试 {retry + 1}/{max_retries}): {e}')
            except requests.exceptions.ConnectTimeout as e:
                logger.debug(f'代理 {ip}:{port} 连接超时 (重试 {retry + 1}/{max_retries}): {e}')
            except requests.exceptions.ReadTimeout as e:
                logger.debug(f'代理 {ip}:{port} 读取超时 (重试 {retry + 1}/{max_retries}): {e}')
            except Exception as e:
                logger.debug(f'代理 {ip}:{port} 测试失败 (重试 {retry + 1}/{max_retries}): {e}')
            
            if retry < max_retries - 1:
                time.sleep(1)  # 重试前等待1秒
        
        logger.debug(f'代理 {ip}:{port} 测试失败，已重试 {max_retries} 次')
        return False

    def http_proxy_utils(self, ip, port):
        """
        专属http链接的代理格式
        @param ip:
        @param port:
        @return:
        """
        proxyMeta = "http://%(host)s:%(port)s" % {

            "host": ip,
            "port": port,
        }

        proxies = {

            "http": proxyMeta,
            "https": proxyMeta
        }
        return proxies

    def key_proxy_utils(self):
        """
        专属http链接的代理格式
        @param ip:
        @param port:
        @return:
        """

        proxyMeta = "http://%(user)s:%(pass)s@%(host)s:%(port)s" % {
            "host": spider_config.PROXY_HOST,
            "port": spider_config.PROXY_PORT,
            "user": spider_config.KEY_ID,
            "pass": spider_config.KEY_KEY,
        }

        proxies = {
            "http": proxyMeta,
            "https": proxyMeta,
        }
        return proxies

    def replace_search_html(self, page_source, file_map):
        """
        替换html文本，根据加密字体文件映射替换page source加密代码
        :param page_source:
        :param file_map:
        :return:
        """
        for k_f, v_f in file_map.items():
            font_map = get_map(v_f)
            for k, v in font_map.items():
                key = str(k).replace('uni', '&#x')
                key = '"' + str(k_f) + '">' + key + ';'
                value = '"' + str(k_f) + '">' + v
                page_source = page_source.replace(key, value)
        return page_source

    def replace_review_html(self, page_source, file_map):
        """
        替换html文本，根据加密字体文件映射替换page source加密代码
        :param page_source:
        :param file_map:
        :return:
        """
        for k_f, v_f in file_map.items():
            font_map = get_map(v_f)
            for k, v in font_map.items():
                key = str(k).replace('uni', '&#x')
                key = '"' + str(k) + '"><'
                value = '"' + str(k) + '">' + str(v) + '<'
                page_source = page_source.replace(key, value)
        return page_source

    def replace_json_text(self, json_text, file_map):
        """
        替换json文本，根据加密字体文件映射替换json加密文本
        :param page_source:
        :param file_map:
        :return:
        """
        for k_f, v_f in file_map.items():
            font_map = get_map(v_f)
            for k, v in font_map.items():
                key = str(k).replace('uni', '&#x')
                key = '\\"' + str(k_f) + '\\">' + key + ';'
                value = '\\"' + str(k_f) + '\\">' + v
                json_text = json_text.replace(key, value)
        return json_text

    def update_cookie(self):
        self.cookie = global_config.getRaw('config', 'Cookie')


requests_util = RequestsUtils()
