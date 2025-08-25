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

from utils.logger import logger
from utils.spider_config import spider_config


class DataBaseUtils():
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
                详情链接 VARCHAR(255),
                图片链接 VARCHAR(255),
                店铺均分 VARCHAR(50),
                推荐菜   VARCHAR(100),
                店铺总分 VARCHAR(50),
                店铺电话 VARCHAR(50),
                其他信息 VARCHAR(255),
                优惠券信息 VARCHAR(255),
                店铺纬度 Double DEFAULT 0,
                店铺经度 Double DEFAULT 0,
                detail TINYINT DEFAULT 0,
                review TINYINT DEFAULT 0
            ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
        ''')
        self.conn.commit()

    def get_no_detail(self):
        """
        获取没有爬取detail的条数
        """
        res = []
        self.cursor.execute("SELECT * FROM info WHERE detail = 0")
        return self.cursor.fetchall()

    def update_no_detail(self, sid):
        """
        更新数据库信息
        """
        self.cursor.execute("UPDATE info SET detail = 1 WHERE 店铺id = %s", (sid,))
        self.conn.commit()

    def get_no_review(self):
        """
        获取没有爬取review的条数
        """
        self.cursor.execute("SELECT * FROM info WHERE review = 0")
        return self.cursor.fetchall()

    def update_no_review(self, sid):
        """
        更新数据库信息
        """
        self.cursor.execute("UPDATE info SET review = 1 WHERE 店铺id = %s", (sid,))
        self.conn.commit()
        
    def __del__(self):
        """析构函数，确保关闭数据库连接"""
        if hasattr(self, 'cursor') and self.cursor:
            self.cursor.close()
        if hasattr(self, 'conn') and self.conn:
            self.conn.close()