# -*- coding: utf-8 -*-
"""
PPE 国内权威文献爬虫（国家哲学社会科学文献中心 NSSD）
====================================================
数据源: 国家哲学社会科学文献中心  https://www.ncpssd.cn/
        中国社科院主办的国家级哲学社会科学文献平台，免费开放。

抓取内容: 政治学 / 经济学 / 哲学 三个学科的最新文献元数据
          （标题、作者、来源期刊、年份、摘要、类型、是否核心期刊、阅读链接）

文献类型流（与 NSSD 前端"资源类型"筛选一致）:
    核心期刊  TYPE="中文期刊文章" AND RANE=*   -> 仅 CSSCI/核心期刊 中文论文
    集刊文章  TYPE="集刊文章"                   -> 学术集刊 / 辑刊论文
    优先发布  synUpdateType:2                   -> 官网优先发布的论文（最新）

    另加 NSSD 学科分类筛选 CLAS=*...* ，用官方分类精确圈定学科范围
    （政治学=政治法律，经济学=经济管理，哲学=哲学宗教）。

用法:
    python ppe_nssd_crawler.py                 # 抓取全部学科
    python ppe_nssd_crawler.py --only 经济学   # 只抓单个学科
    python ppe_nssd_crawler.py --pages 2       # 每学科抓 2 页(每页10条)
    python ppe_nssd_crawler.py --core-only     # 只抓核心期刊流
    python ppe_nssd_crawler.py --no-clas       # 不用学科分类精确筛选

输出:
    nssd_data.json  <- 原始数据
    nssd_data.js    <- 供 index.html 以 <script> 加载(默认生成，--no-js 关闭)
    nssd_crawler.log

说明:
    - 接口为 NSSD 公开搜索接口（searchHandler/search），无需登录
    - 检索表达式、排序方式、类型/学科/核心期刊过滤均与官网前端一致
    - 已做限速(每次请求间隔 1.2s)与重试，请勿高频抓取，尊重对方服务
"""
import argparse
import json
import os
import re
import sys
import time
from datetime import datetime

import requests

BASE_URL = "https://www.ncpssd.cn"
SEARCH_URL = BASE_URL + "/searchHandler/search"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")

# 学科检索词（在 NSSD 标题/主题等字段中匹配）
DISCIPLINES = {
    "政治学": ["政治", "政治学", "民主", "治理", "政党", "公共政策"],
    "经济学": ["经济", "经济学", "货币", "财政", "市场", "贸易"],
    "哲学":   ["哲学", "伦理学", "形而上学", "认识论", "美学"],
}

# 学科分类（NSSD 前端"学科分类"筛选取值，用官方分类精确圈定学科范围）
DISCIPLINE_CLAS = {
    "政治学": "D,E126,E266,DF",   # 政治法律
    "经济学": "F,C8,C9",          # 经济管理
    "哲学":   "B,A,D917.2,G44",   # 哲学宗教
}

# 文献类型流（与 NSSD 前端"资源类型"筛选一致）
#   expr : 附加检索条件（搜索接口语法）
#   cap  : 每学科该类型最多保留条数
STREAMS = [
    {"name": "核心期刊", "expr": '(TYPE="中文期刊文章" AND RANE=*)', "cap": 30},
    {"name": "集刊文章", "expr": 'TYPE="集刊文章"',                   "cap": 12},
    {"name": "优先发布", "expr": "synUpdateType:2",                   "cap": 4},
]

OUT_FILE = "nssd_data.json"
LOG_FILE = "nssd_crawler.log"


def log(msg):
    line = "[{}] {}".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), msg)
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def clean_html(text):
    """去掉 <font>、<b> 等高亮标签，还原纯文本"""
    if not text:
        return ""
    t = re.sub(r"<[^>]+>", "", str(text))
    t = t.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    t = re.sub(r"\s+", " ", t).strip()
    return t


def strip_citation(s):
    """去掉作者名后的 [1] 上标"""
    return re.sub(r"\[\d+\]", "", s or "").strip()


def build_search_query(keyword):
    """构造与 NSSD 前端一致的检索表达式（多字段 OR）"""
    fields = ["IKTE", "IKPYTE", "IKST", "IKET", "IKSE"]
    inner = " OR ".join('{}="{}"'.format(f, keyword) for f in fields)
    return "({})".format(inner)


def build_expr(keyword, clas, stream_expr):
    """组装完整检索表达式：关键词 AND 学科分类 AND 文献类型流"""
    parts = [build_search_query(keyword)]
    if clas:
        parts.append("CLAS=*{}*".format(clas))
    if stream_expr:
        parts.append(stream_expr)
    return " AND ".join(parts)


def search(expr, page_num, page_size):
    """调用 NSSD 搜索接口，返回 rows 列表"""
    data = {
        "search": expr,
        "pageNum": page_num,
        "pageSize": page_size,
        "sort": "synUpdateType|DESC,date|DESC,ik_subject|DESC,id|DESC",
        "sType": 0,
        "ajaxKeys": "",
        "customShowCondition": "",
    }
    headers = {"User-Agent": UA, "Referer": BASE_URL + "/index.html"}
    r = requests.post(SEARCH_URL, data=data, headers=headers, timeout=30)
    r.raise_for_status()
    j = r.json()
    if not j.get("succee") and not j.get("result"):
        raise RuntimeError("NSSD 返回失败: {}".format(j))
    d = j.get("data") or {}
    return d.get("rows") or [], d.get("total") or 0


def row_to_paper(row, stream_name):
    """将 NSSD 原始行清洗为标准 paper 结构"""
    paper_id = row.get("data_id") or row.get("id") or ""
    return {
        "title": clean_html(row.get("ik_title") or row.get("title") or ""),
        "title_en": clean_html(
            "；".join((row.get("title_auto") or [])[1:2]) if isinstance(row.get("title_auto"), list) else ""
        ),
        "authors": [strip_citation(a) for a in
                    re.split(r"[;；]", clean_html(row.get("ik_creator") or "")) if strip_citation(a)],
        "journal": clean_html(row.get("cbw_name") or ""),
        "year": str(row.get("years") or ""),
        "abstract": clean_html(row.get("ik_remark") or "")[:400],
        "type": clean_html(row.get("type") or ""),
        "subject": clean_html(row.get("ik_subject") or ""),
        "stream": stream_name,          # 来源流：核心期刊 / 集刊文章 / 优先发布
        "core": stream_name == "核心期刊",  # 是否核心期刊
        "id": paper_id,
        "link": "https://www.ncpssd.cn/Literature/readurl?id={}".format(paper_id) if paper_id else "",
        "source": "国家哲学社会科学文献中心",
    }


def crawl_discipline(discipline, keywords, pages, page_size, clas, streams):
    """抓取一个学科：对每个关键词 x 每个文献类型流，取前 pages 页，去重"""
    seen = {}
    for st in streams:
        for kw in keywords:
            expr = build_expr(kw, clas, st["expr"])
            log("  学科[{}] 关键词[{}] 类型[{}] 抓取中...".format(discipline, kw, st["name"]))
            for p in range(1, pages + 1):
                try:
                    rows, total = search(expr, p, page_size)
                    if not rows:
                        break
                    for row in rows:
                        paper = row_to_paper(row, st["name"])
                        # (标题,年份,类型) 去重：核心/优先发布同文只留先到的
                        key = (paper["title"], paper["year"], paper["type"])
                        if key in seen:
                            continue
                        seen[key] = paper
                    time.sleep(1.2)  # 限速，礼貌抓取
                except requests.RequestException as e:
                    log("  请求失败: {} 关键词[{}] 类型[{}] 第{}页 错误: {}"
                        .format(discipline, kw, st["name"], p, e))
                    time.sleep(3)
                except RuntimeError as e:
                    log("  接口异常: {}".format(e))
                    time.sleep(3)
    papers = sorted(seen.values(), key=lambda x: x["year"], reverse=True)

    # 按文献类型流配额裁剪：每流保留前 cap 篇
    result = []
    for st in streams:
        grp = [pp for pp in papers if pp.get("stream") == st["name"]]
        result.extend(grp[:st["cap"]])
    result.sort(key=lambda x: x["year"], reverse=True)
    log("  学科[{}] 共获取 {} 篇（含核心 {} 篇、集刊 {} 篇、优先发布 {} 篇）".format(
        discipline, len(result),
        sum(1 for x in result if x["stream"] == "核心期刊"),
        sum(1 for x in result if x["stream"] == "集刊文章"),
        sum(1 for x in result if x["stream"] == "优先发布")))
    return result


def main():
    ap = argparse.ArgumentParser(description="PPE 国内权威文献爬虫（NSSD）")
    ap.add_argument("--only", choices=list(DISCIPLINES.keys()), help="只抓取指定学科")
    ap.add_argument("--pages", type=int, default=1, help="每学科每关键词抓取页数(默认1)")
    ap.add_argument("--core-only", action="store_true",
                    help="只抓核心期刊流（CSSCI/核心期刊）")
    ap.add_argument("--no-clas", action="store_true",
                    help="不使用 NSSD 学科分类精确筛选")
    ap.add_argument("--out", default=OUT_FILE, help="输出 JSON 文件")
    ap.add_argument("--no-js", action="store_true",
                    help="同时生成 nssd_data.js（供 index.html 在 file:// 下加载）")
    args = ap.parse_args()

    targets = {args.only: DISCIPLINES[args.only]} if args.only else DISCIPLINES
    streams = [STREAMS[0]] if args.core_only else STREAMS

    log("=== 开始抓取 NSSD，学科: {}，每关键词页数: {}，类型流: {}，学科分类: {} ===".format(
        ",".join(targets), args.pages,
        ",".join(st["name"] for st in streams),
        "关闭" if args.no_clas else "开启"))

    result = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source": "国家哲学社会科学文献中心 (https://www.ncpssd.cn/)",
        "note": "中国社科院主办的国家级哲学社会科学文献平台，免费开放。"
                "已按 NSSD 官方学科分类筛选，含核心期刊 / 集刊 / 优先发布文献。",
        "disciplines": {},
    }

    try:
        for disc, keywords in targets.items():
            clas = None if args.no_clas else DISCIPLINE_CLAS.get(disc)
            result["disciplines"][disc] = crawl_discipline(
                disc, keywords, args.pages, 10, clas, streams)
    except Exception as e:
        log("抓取异常: {}".format(e))
        raise

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    log("已写入 JSON: {}".format(args.out))

    # 同时生成 nssd_data.js，供 index.html 以 <script> 标签加载（file:// 下可用）
    if not args.no_js:
        js_out = os.path.splitext(args.out)[0] + ".js"
        js_content = "// 由 ppe_nssd_crawler.py 生成，请勿手动编辑\n" \
                     "window.NSSD_DATA = {};\n".format(
                         json.dumps(result, ensure_ascii=False))
        with open(js_out, "w", encoding="utf-8") as f:
            f.write(js_content)
        log("已写入 JS: {}".format(js_out))

    total = sum(len(v) for v in result["disciplines"].values())
    log("=== 完成！共 {} 篇 ===".format(total))
    log("提示：请勿高频运行本脚本，尊重 NSSD 服务。")


if __name__ == "__main__":
    main()
