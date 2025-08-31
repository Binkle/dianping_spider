#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    try:
        import pymysql
        print("✅ pymysql 模块已安装")
    except ImportError:
        print("❌ pymysql 模块未安装，请运行: pip install pymysql")
        return
    
    import json
    from dianping_spider.utils.spider_config import spider_config
    
    jsonl_file = "dianping_spider/files/amap_poi.jsonl"
    if not os.path.exists(jsonl_file):
        print(f"❌ JSONL文件不存在: {jsonl_file}")
        return
    
    print(f"✅ JSONL文件存在: {jsonl_file}")
    
    # 读取并显示数据
    with open(jsonl_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        print(f"✅ JSONL文件包含 {len(lines)} 条数据")
        
        # 显示前3条
        for i, line in enumerate(lines[:3], 1):
            try:
                data = json.loads(line.strip())
                print(f"  {i}. {data.get('name', 'N/A')} - {data.get('cityname', 'N/A')}")
            except:
                print(f"  {i}. 解析失败")
    
    # 测试数据库配置
    print(f"数据库配置:")
    print(f"  Host: {spider_config.MYSQL_HOST}")
    print(f"  Port: {spider_config.MYSQL_PORT}")
    print(f"  User: {spider_config.MYSQL_USER}")
    print(f"  Database: {spider_config.MYSQL_DATABASE}")
    
    # 尝试连接数据库
    try:
        conn = pymysql.connect(
            host=spider_config.MYSQL_HOST,
            port=spider_config.MYSQL_PORT,
            user=spider_config.MYSQL_USER,
            password=spider_config.MYSQL_PASSWORD,
            database=spider_config.MYSQL_DATABASE,
            charset='utf8mb4'
        )
        print("✅ 数据库连接成功")
        
        cursor = conn.cursor()
        
        # 创建表
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS amap_poi (
            id VARCHAR(50) PRIMARY KEY,
            name VARCHAR(500),
            address TEXT,
            location VARCHAR(100),
            pname VARCHAR(100),
            cityname VARCHAR(100),
            adname VARCHAR(100),
            adcode VARCHAR(20),
            pcode VARCHAR(20),
            citycode VARCHAR(20),
            type TEXT,
            typecode VARCHAR(50),
            parent VARCHAR(500),
            distance VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
        cursor.execute(create_table_sql)
        print("✅ 表创建完成")
        
        # 插入数据
        inserted = 0
        with open(jsonl_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                    
                try:
                    data = json.loads(line)
                    
                    # 检查是否已存在
                    cursor.execute("SELECT id FROM amap_poi WHERE id = %s", (data.get('id'),))
                    if cursor.fetchone():
                        continue
                    
                    # 插入数据
                    insert_sql = """
                    INSERT INTO amap_poi (
                        id, name, address, location, pname, cityname, adname,
                        adcode, pcode, citycode, type, typecode, parent, distance
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    cursor.execute(insert_sql, (
                        data.get('id'), data.get('name'), data.get('address'),
                        data.get('location'), data.get('pname'), data.get('cityname'),
                        data.get('adname'), data.get('adcode'), data.get('pcode'),
                        data.get('citycode'), data.get('type'), data.get('typecode'),
                        data.get('parent'), data.get('distance')
                    ))
                    inserted += 1
                    
                except Exception as e:
                    print(f"插入失败: {e}")
        
        conn.commit()
        
        # 检查结果
        cursor.execute("SELECT COUNT(*) FROM amap_poi")
        count = cursor.fetchone()[0]
        print(f"✅ 成功插入 {inserted} 条数据，表中共有 {count} 条数据")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ 数据库操作失败: {e}")

if __name__ == "__main__":
    main()