# -*- coding:utf-8 -*-
import argparse
import os

from dianping_spider.utils.logger import logger
from .tiler import Rectangle
from .crawler import AMapCrawler
from .district import get_city_rectangles
from .exporter import jsonl_to_csv


def parse_args():
    ap = argparse.ArgumentParser(description="AMap newpoisearch 抓取（自适应切分，types=050000|110000）")
    ap.add_argument("--types", type=str, default="050000|110000", help="AMap types 列表(竖线或逗号分隔)")
    ap.add_argument("--bbox", type=str, default="73.5,18.0,135.1,53.6",
                    help="根矩形: min_lng,min_lat,max_lng,max_lat")
    ap.add_argument("--city", type=str, default="", help="按城市/城市adcode抓取，如'北京市'或'110000'")
    ap.add_argument("--page-size", type=int, default=25, help="每页条数(1-25)")
    ap.add_argument("--max-pages", type=int, default=8, help="同参最多8页(<=200)")
    ap.add_argument("--base-pages", type=int, default=3, help="低密度仅抓前N页，满页再扩到max-pages")
    ap.add_argument("--max-requests", type=int, default=5000, help="本轮请求预算上限")
    ap.add_argument("--max-depth", type=int, default=18, help="最大切分深度")
    ap.add_argument("--out", type=str, default="dianping_spider/files/amap_poi.jsonl", help="输出jsonl路径")
    ap.add_argument("--state", type=str, default="dianping_spider/files/amap_state.json", help="断点状态文件")
    ap.add_argument("--no-resume", action="store_true", help="忽略已有状态，重新开始")
    ap.add_argument("--priority-queue", action="store_true", help="使用优先级队列(高密度/小面积优先)")
    ap.add_argument("--use-kd", action="store_true", help="使用KD二分（默认四叉）")
    ap.add_argument("--allow-adcode", type=str, default="", help="仅保留这些adcode(逗号分隔)")
    ap.add_argument("--allow-city", type=str, default="", help="仅保留这些cityname(逗号分隔)")
    # 热门区域优先（多城市种子）
    ap.add_argument("--city-list", type=str, default="",
                    help="热门区域列表（逗号分隔，名称或adcode均可），会作为高优先级种子先抓")
    ap.add_argument("--seed-file", type=str, default="",
                    help="热门区域文件，每行一个名称或adcode")
    ap.add_argument("--seed-priority", type=float, default=-10.0,
                    help="种子区域的初始优先级（越小越优先，默认-10）")
    # 输出与入库
    ap.add_argument("--export-csv", action="store_true", help="完成后导出为CSV")
    ap.add_argument("--csv-path", type=str, default="", help="CSV导出路径(默认与jsonl同名)")
    ap.add_argument("--write-mysql", action="store_true", help="边抓边入库到MySQL")
    ap.add_argument("--mysql-table", type=str, default="amap_poi", help="MySQL表名")
    ap.add_argument("--mysql-batch", type=int, default=50, help="MySQL批量写入大小")
    ap.add_argument("--no-jsonl", action="store_true", help="不写JSONL，仅入库MySQL")
    return ap.parse_args()


def build_crawler(args, allowed_adcodes=None, allowed_cities=None):
    key = os.environ.get("AMAP_KEYS") or os.environ.get("AMAP_KEY", "")
    if not key or not key.strip():
        logger.error("请先导出环境变量 AMAP_KEY 或 AMAP_KEYS")
        return None

    crawler = AMapCrawler(
        key=key,
        out_path=args.out,
        state_path=args.state,
        types=args.types,
        page_size=max(1, min(25, args.page_size)),
        max_pages=max(1, args.max_pages),
        max_requests=max(1, args.max_requests),
        max_depth=max(1, args.max_depth),
        resume=not args.no_resume,
        use_priority_queue=args.priority_queue,
        use_kd_split=args.use_kd,
        base_pages=max(1, args.base_pages),
        allowed_adcodes=allowed_adcodes or [],
        allowed_cities=allowed_cities or [],
        write_mysql=args.write_mysql,
        mysql_table=args.mysql_table,
        mysql_batch=max(1, args.mysql_batch),
        write_jsonl=not args.no_jsonl,
    )
    return crawler


def _load_seed_tokens(args):
    tokens = []
    if args.city_list:
        tokens += [x.strip() for x in args.city_list.split(",") if x.strip()]
    if args.seed_file and os.path.exists(args.seed_file):
        with open(args.seed_file, "r", encoding="utf-8") as f:
            for line in f:
                t = line.strip()
                if t:
                    tokens.append(t)
    return tokens


def _seed_hot_regions(crawler: AMapCrawler, tokens: list, seed_priority: float):
    if not tokens:
        return
    
    success_count = 0
    logger.info(f"为热门区域建立种子，共 {len(tokens)} 个")
    
    for tok in tokens:
        if not tok.strip():
            continue
            
        try:
            districts = get_city_rectangles(tok)
            if not districts:
                logger.warning(f"未找到区域: {tok}")
                continue
                
            rect_count = 0
            for name, code, rects in districts:
                for rect in rects:
                    if rect.width() <= 0 or rect.height() <= 0:
                        continue
                    crawler.add_seed(rect, depth=0, priority=seed_priority)
                    rect_count += 1
                    
            if rect_count > 0:
                success_count += 1
                logger.info(f"种子区域 '{tok}' 添加了 {rect_count} 个矩形")
            else:
                logger.warning(f"种子区域 '{tok}' 未找到有效矩形")
                
        except Exception as e:
            logger.warning(f"种子区域解析失败 '{tok}': {e}")
            
    logger.info(f"热门区域种子添加完成: {success_count}/{len(tokens)} 成功")


def main():
    args = parse_args()

    # 指定过滤条件
    allow_adcodes = [x.strip() for x in args.allow_adcode.split(",") if x.strip()]
    allow_cities = [x.strip() for x in args.allow_city.split(",") if x.strip()]

    seed_tokens = _load_seed_tokens(args)

    if args.city:
        logger.info(f"按城市抓取: {args.city}")
        try:
            districts = get_city_rectangles(args.city)
            if not districts:
                logger.error(f"未找到城市 '{args.city}' 的区县信息")
                return

            # 自动将城市的所有区县 adcode 作为允许列表（可与用户传入的取并集）
            # 自动将城市的所有区县 adcode 作为允许列表（可与用户传入的取并集）
            auto_adcodes = [str(code) for _, code, _ in districts]
            # 同时添加城市本身的adcode
            auto_adcodes.append(args.city)
            if allow_adcodes:
                allow_adcodes = sorted(set(allow_adcodes) | set(auto_adcodes))
            else:
                allow_adcodes = auto_adcodes
            
            logger.info(f"允许的adcodes: {allow_adcodes}")

            crawler = build_crawler(args, allowed_adcodes=allow_adcodes, allowed_cities=allow_cities)
            if crawler is None:
                return

            # 额外热门区域种子
            _seed_hot_regions(crawler, seed_tokens, args.seed_priority)

            # 按区县边界的包络矩形抓取
            for name, code, rects in districts:
                for i, rect in enumerate(rects):
                    logger.info(f"开始抓取区县: {name}({code}) 边界 {i+1}/{len(rects)}")
                    crawler.crawl(rect)

        except Exception as e:
            logger.error(f"按城市抓取失败: {e}")
            return
    else:
        # 按矩形抓取（全国或自定义 bbox）
        min_lng, min_lat, max_lng, max_lat = [float(x) for x in args.bbox.split(",")]
        root = Rectangle(min_lng, min_lat, max_lng, max_lat)

        crawler = build_crawler(args, allowed_adcodes=allow_adcodes, allowed_cities=allow_cities)
        if crawler is None:
            return

        # 先入队热门区域种子（高优先级）
        _seed_hot_regions(crawler, seed_tokens, args.seed_priority)

        # 再抓 root 覆盖全国
        crawler.crawl(root)

    if args.export_csv:
        csv_path = args.csv_path if args.csv_path else None
        logger.info(f"导出CSV: {args.out} -> {csv_path or '(自动)'}")
        ok = jsonl_to_csv(args.out, csv_path)
        logger.info("CSV导出成功" if ok else "CSV导出失败")


if __name__ == "__main__":
    main()