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
import sys
import time
import random

from bs4 import BeautifulSoup

from utils.logger import logger
from utils.get_font_map import get_search_map_file
from utils.requests_utils import requests_util
from utils.spider_config import spider_config
from utils.session_manager import session_manager
from utils.param_generator import param_generator
from utils.advanced_anti_detection import advanced_anti_detection


class Search():
    def __init__(self):
        self.is_ban = False

    def search(self, search_url, request_type='proxy, cookie', last_chance=False):
        """
        搜索，使用高级反检测策略
        :param search_url: 搜索URL
        :param request_type: 请求类型
        :param last_chance: 是否最后一次机会
        :return:
        """
        if self.is_ban and spider_config.USE_COOKIE_POOL is False:
            logger.warning('搜索页请求被ban，程序终止')
            sys.exit()

        # 使用高级反检测策略
        logger.info("使用高级反检测策略进行搜索")
        
        # 模拟真实的搜索行为流程
        r = advanced_anti_detection.simulate_search_behavior(search_url)
        
        if r is None:
            logger.error("高级反检测策略失败")
            if last_chance:
                self.is_ban = True
                return None
            # 重试一次，但使用传统方法
            logger.info("尝试使用传统方法重试")
            time.sleep(random.uniform(10, 20))  # 长时间等待
            return self.search(search_url=search_url, request_type=request_type, last_chance=True)
        
        # 检查响应质量
        is_good, message = advanced_anti_detection.check_response_quality(r)
        if not is_good:
            logger.warning(f"响应质量检查失败: {message}")
            if last_chance:
                self.is_ban = True
                return None
            return self.search(search_url=search_url, request_type=request_type, last_chance=True)
        # 给一次retry的机会，如果依然403则判断为被ban
        if r.status_code == 403:
            if last_chance is True:
                self.is_ban = True
            return self.search(search_url=search_url, request_type=request_type, last_chance=True)
        text = r.text
        # 获取加密文件
        file_map = get_search_map_file(text)
        # 替换加密文件
        text = requests_util.replace_search_html(text, file_map)

        # 网页解析
        html = BeautifulSoup(text, 'lxml')
        # 如果页面出现了not-found(无数据)提示，返回None给上一层，让上一层的for循环退出
        if html.select(".not-found-right"):
            return None
        shop_all_list = html.select('.shop-list')[0].select('li')

        search_res = []
        for shop in shop_all_list:
            try:
                image_path = shop.select('.pic')[0].select('a')[0].select('img')[0]['src']
            except:
                image_path = '-'
            try:
                shop_id = shop.select('.txt')[0].select('.tit')[0].select('a')[0]['data-shopid']
            except:
                shop_id = '-'
            try:
                detail_url = shop.select('.txt')[0].select('.tit')[0].select('a')[0]['href']
            except:
                detail_url = '-'
            try:
                name = shop.select('.txt')[0].select('.tit')[0].select('a')[0].text.strip()
            except:
                name = '-'
            # 两个star方式，有的页面显示详细star分数，有的显示icon
            # 解析icon
            try:
                star_point = \
                    shop.select('.txt')[0].select('.comment')[0].select('.star_icon')[0].select('span')[0]['class'][
                        1].split('_')[1]
                star_point = float(star_point) / 10
                star_point = str(star_point)
            except:
                star_point = '-'
            # 解析详细star
            try:
                star_point = \
                    shop.select('.txt')[0].select('.comment')[0].select('.star_score')[0].text
                star_point = float(star_point)
                star_point = str(star_point)
            except:
                pass
            try:
                review_number = shop.select('.txt')[0].select('.comment')[0].select('.review-num')[0].text.replace(
                    '\n', '')
            except:
                review_number = '-'
            try:
                mean_price = shop.select('.txt')[0].select('.comment')[0].select('.mean-price')[0].select('b')[
                    0].text
            except:
                mean_price = '￥0'
            try:
                tags = shop.select('.txt')[0].select('.tag-addr')[0].select('.tag')
                tag1 = tags[0].text.replace('\n', ' ').strip()
                tag2 = tags[1].text.replace('\n', ' ').strip()
            except:
                tag1 = '-'
                tag2 = '-'
            try:
                addr = shop.select('.txt')[0].select('.tag-addr')[0].select('.addr')[0].text.replace('\n',
                                                                                                     ' ').strip()
            except:
                addr = '-'
            try:
                recommend = shop.select('.recommend')[0].text.replace('\n', ' ').strip()
            except:
                recommend = '-'
            try:
                comment_list = shop.select('.comment-list')[0].text.replace('\n', ' ').strip()
            except:
                comment_list = '-'
            one_step_search_res = {
                '店铺id': shop_id,
                '店铺名': name,
                '评论总数': review_number,
                '人均价格': mean_price,
                '标签1': tag1,
                '标签2': tag2,
                '店铺地址': addr,
                '详情链接': detail_url,
                '图片链接': image_path,
                '店铺均分': comment_list,
                '推荐菜': recommend,
                '店铺总分': star_point,
            }
            search_res.append(one_step_search_res)
            # yield one_step_search_res
        return search_res
