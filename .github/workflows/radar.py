import os
import time
import urllib.parse
from datetime import datetime, timezone, timedelta

import requests
import feedparser

SENDKEY = os.environ["SENDKEY"]
UA = "Mozilla/5.0 (compatible; WaterRadar/1.0)"


def gnews(query):
    """构造 Google 新闻 RSS 链接（境外服务器可稳定访问，返回中文新闻）"""
    q = urllib.parse.quote(query)
    return f"https://news.google.com/rss/search?q={q}&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"


# 信息源：每条是一个关键词查询，可自行增删
SOURCES = [
    ("福建水利招标", gnews("福建 水利 招标")),
    ("防洪评价", gnews("防洪评价 OR 防洪影响评价")),
    ("水资源论证", gnews("水资源论证")),
    ("水库大坝", gnews("水库 除险加固 OR 大坝 安全鉴定")),
    ("智慧水利前沿", gnews("智慧水利 OR 数字孪生 水利")),
]

# 正向词：命中其一才算相关
POSITIVE = [
    "水利", "防洪", "防洪评价", "水资源论证", "水库", "大坝", "除险加固", "安全鉴定",
    "河道", "堤防", "水文", "设计洪水", "水土保持", "灌区", "泵站", "水闸",
    "招标", "中标", "比选", "采购", "可研", "初步设计", "勘察设计",
    "数字孪生", "智慧水利",
]

# 强排除词：命中其一直接丢弃
NEG_HARD = [
    "物业", "保洁", "绿化", "食堂", "餐饮", "办公用品", "印刷", "车辆", "保安",
    "招聘", "培训", "饮用水采购", "空调", "家具", "房地产", "楼盘",
]


def keep(title):
    if any(n in title for n in NEG_HARD):
        return False
    return any(p in title for p in POSITIVE)


CN = timezone(timedelta(hours=8))
NOW = datetime.now(timezone.utc)
WINDOW_HOURS = 26  # 只保留最近 26 小时的新闻，配合每天跑一次，天然去重


def recent(entry):
    t = entry.get("published_parsed") or entry.get("updated_parsed")
    if not t:
        return True
    pub = datetime(*t[:6], tzinfo=timezone.utc)
    return (NOW - pub) <= timedelta(hours=WINDOW_HOURS)


def push(title, desp):
    try:
        r = requests.post(
            f"https://sctapi.ftqq.com/{SENDKEY}.send",
            data={"title": title, "desp": desp},
            timeout=20,
        )
        print("push:", r.status_code, r.text[:200])
    except Exception as ex:
        print("push failed:", ex)


def main():
    seen = set()
    items = []
    for name, url in SOURCES:
        try:
            d = feedparser.parse(url, agent=UA)
        except Exception as ex:
            print(f"[WARN] {name} 抓取失败: {ex}")
            continue
        for e in d.entries:
            title = (e.get("title") or "").strip()
            link = e.get("link") or ""
            if not title or title in seen:
                continue
            if recent(e) and keep(title):
                seen.add(title)
                items.append((name, title, link))
        time.sleep(1)

    if items:
        lines = [f"### 🌊 福建水利情报 · {datetime.now(CN):%m-%d}", ""]
        for name, title, link in items[:30]:
            lines.append(f"- [{title}]({link})  `{name}`")
        push(f"水利情报 {len(items)} 条", "\n".join(lines))
    else:
        push("水利雷达运行正常", "今天暂无符合关键词的新内容。")


if __name__ == "__main__":
    main()
