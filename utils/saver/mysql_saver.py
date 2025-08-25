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
import json

# from utils.config import global_config
from utils.logger import logger
from utils.spider_config import spider_config


class MySQLSaver():
    def __init__(self):
        try:
            import pymysql
            self.conn = pymysql.connect(
                host=spider_config.MYSQL_HOST,
                port=spider_config.MYSQL_PORT,
                user=spider_config.MYSQL_USER,
                password=spider_config.MYSQL_PASSWORD,
                database=spider_config.MYSQL_DATABASE,
                charset='utf8mb4'
            )
            self.cursor = self.conn.cursor(pymysql.cursors.DictCursor)
            
            # 确保表存在
            self._create_tables_if_not_exist()
            
        except Exception as e:
            logger.warning(
                f'系统中可能没有安装或启动MySQL数据库，请先根据系统环境安装或启动MySQL，再运行程序。错误信息: {str(e)}')
            sys.exit()
    
    def _create_tables_if_not_exist(self):
        """创建必要的数据表"""
        # 创建info表
        self.cursor.execute('''
                    CREATE TABLE IF NOT EXISTS info (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        店铺id VARCHAR(50) UNIQUE,
                        店铺名 VARCHAR(255),
                        评论总数 VARCHAR(255),
                        人均价格 VARCHAR(255),
                        标签1 VARCHAR(255),
                        标签2 VARCHAR(255),
                        店铺地址 VARCHAR(255),
                        详情链接 VARCHAR(255),
                        图片链接 VARCHAR(255),
                        店铺均分 VARCHAR(50),
                        推荐菜   VARCHAR(100),
                        店铺总分 VARCHAR(50),
                        店铺电话 VARCHAR(50),
                        其他信息 VARCHAR(255),
                        优惠券信息 VARCHAR(255),
                        店铺纬度 VARCHAR(255),
                        店铺经度 VARCHAR(255),
                        detail TINYINT DEFAULT 0,
                        review TINYINT DEFAULT 0
            ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
        ''')
        
        # 创建info_detail表
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS info_detail (
                id INT AUTO_INCREMENT PRIMARY KEY,
                店铺id VARCHAR(50) UNIQUE,
                详细信息 TEXT,
                营业时间 VARCHAR(255),
                特色菜 TEXT
            ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
        ''')
        
        # 创建review表
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS review (
                id INT AUTO_INCREMENT PRIMARY KEY,
                店铺id VARCHAR(50),
                评论id VARCHAR(50),
                用户名 VARCHAR(100),
                评分 FLOAT,
                评论内容 TEXT,
                评论时间 DATETIME,
                INDEX (店铺id)
            ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
        ''')
        
        self.conn.commit()

    def save_data(self, data, data_type):
        """
        保存数据
        :param data:
        :param data_type:
        :return:
        """
        assert data_type in ['search', 'detail', 'review']
        if data_type == 'search':
            self.save_search_list(data)
        elif data_type == 'detail':
            self.save_detail_list(data)
        elif data_type == 'review':
            self.save_review_list(data)
        else:
            raise Exception

    def save_search_list(self, data):
        """
        保存搜索结果
        :param data:
        :return:
        """
        # 先删除已有数据
        self.cursor.execute("DELETE FROM info WHERE 店铺id = %s", (data['店铺id'],))
    
        # 处理嵌套的字典和列表，将它们转换为JSON字符串
        processed_data = {}
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                processed_data[key] = json.dumps(value, ensure_ascii=False)
            else:
                processed_data[key] = value
    
        # 准备SQL语句和参数
        fields = ', '.join(processed_data.keys())
        placeholders = ', '.join(['%s'] * len(processed_data))
    
        sql = f"INSERT INTO info ({fields}) VALUES ({placeholders})"
        values = tuple(processed_data.values())
    
        # 执行插入
        print(sql)
        print(values)
        self.cursor.execute(sql, values)
        self.conn.commit()

    def save_detail_list(self, data):
        """
        保存详细结果
        :param data:
        :return:
        """
        # 先删除已有数据
        self.cursor.execute("DELETE FROM info_detail WHERE 店铺id = %s", (data['店铺id'],))
        
        # 对于复杂数据结构，可能需要序列化为JSON
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                data[key] = json.dumps(value, ensure_ascii=False)
        
        # 准备SQL语句和参数
        fields = ', '.join(data.keys())
        placeholders = ', '.join(['%s'] * len(data))
        
        sql = f"INSERT INTO info_detail ({fields}) VALUES ({placeholders})"
        values = tuple(data.values())
        
        # 执行插入
        self.cursor.execute(sql, values)
        self.conn.commit()

    def save_review_list(self, data):
        """
        保存评论数据
        :param data:
        :return:
        """
        # 先删除已有数据
        self.cursor.execute("DELETE FROM review WHERE 店铺id = %s", (data['店铺id'],))
        
        # 评论可能是一个列表，需要单独处理
        shop_id = data['店铺id']
        reviews = data.get('评论', [])
        
        if reviews:
            for review in reviews:
                review['店铺id'] = shop_id
                
                # 准备SQL语句和参数
                fields = ', '.join(review.keys())
                placeholders = ', '.join(['%s'] * len(review))
                
                sql = f"INSERT INTO review ({fields}) VALUES ({placeholders})"
                values = tuple(review.values())
                
                # 执行插入
                self.cursor.execute(sql, values)
        
        self.conn.commit()
        
    def __del__(self):
        """析构函数，确保关闭数据库连接"""
        if hasattr(self, 'cursor') and self.cursor:
            self.cursor.close()
        if hasattr(self, 'conn') and self.conn:
            self.conn.close()