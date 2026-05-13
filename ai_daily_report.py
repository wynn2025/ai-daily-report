#!/usr/bin/env python3
"""
AI Daily Report Generator v1.0 - AI日报生成器

功能：自动抓取AI领域热门资讯，生成结构化Markdown日报
数据源：Hacker News / arXiv / GitHub Trending / ProductHunt
"""

import json
import os
import sys
import argparse
import hashlib
import time
import re
from datetime import datetime, timedelta
from pathlib import Path
try:
    from urllib.request import urlopen, Request
    from urllib.error import URLError, HTTPError
    from urllib.parse import quote_plus
except ImportError:
    pass

# ============================================================
# 配置
# ============================================================
VERSION = "1.0.0"
CONFIG = {
    "cache_dir": Path(__file__).parent / ".cache",
    "max_items_per_source": 15,
    "request_timeout": 15,
    "user_agent": "AI-Daily-Report/1.0",
    "default_sources": ["hackernews", "arxiv", "github"],
    "default_keywords": [
        "artificial intelligence", "machine learning", "deep learning",
        "LLM", "GPT", "transformer", "neural network", "AI agent",
        "computer vision", "NLP", "reinforcement learning",
        "diffusion model", "RAG", "fine-tuning", "AI safety"
    ],
    "cn_keywords": [
        "大模型", "人工智能", "机器学习", "深度学习",
        "AI Agent", "多模态", "知识图谱", "自动驾驶"
    ]
}

DEEPSEEK_API = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"


def get_cache_key(source, params=""):
    raw = f"{source}:{params}:{datetime.now().strftime('%Y-%m-%d')}"
    return hashlib.md5(raw.encode()).hexdigest()


def load_cache(key):
    cache_dir = CONFIG["cache_dir"]
    cache_dir.mkdir(exist_ok=True)
    fp = cache_dir / f"{key}.json"
    if fp.exists():
        age = time.time() - fp.stat().st_mtime
        if age < 3600:
            return json.loads(fp.read_text(encoding="utf-8"))
    return None


def save_cache(key, data):
    cache_dir = CONFIG["cache_dir"]
    cache_dir.mkdir(exist_ok=True)
    fp = cache_dir / f"{key}.json"
    fp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def http_get(url, headers=None):
    hdrs = {"User-Agent": CONFIG["user_agent"]}
    if headers:
        hdrs.update(headers)
    req = Request(url, headers=hdrs)
    try:
        with urlopen(req, timeout=CONFIG["request_timeout"]) as resp:
            return resp.read().decode("utf-8")
    except (URLError, HTTPError) as e:
        print(f"  [WARN] Request failed: {url} -> {e}", file=sys.stderr)
        return None


# ============================================================
# 数据源：Hacker News
# ============================================================
def fetch_hackernews(keywords):
    """抓取HN上AI相关的热门文章"""
    print("  Fetching Hacker News...")
    ck = get_cache_key("hackernews")
    cached = load_cache(ck)
    if cached:
        return cached

    items = []
    try:
        data = http_get("https://hacker-news.firebaseio.com/v0/topstories.json")
        if not data:
            return items
        ids = json.loads(data)[:80]

        kw_set = set(k.lower() for k in keywords)
        for i, sid in enumerate(ids[:40]):
            story = http_get(f"https://hacker-news.firebaseio.com/v0/item/{sid}.json")
            if not story:
                continue
            s = json.loads(story)
            title = s.get("title", "")
            text = title.lower()
            score = s.get("score", 0)
            if any(kw in text for kw in kw_set) and score >= 10:
                items.append({
                    "title": title,
                    "url": s.get("url", f"https://news.ycombinator.com/item?id={sid}"),
                    "source": "Hacker News",
                    "score": score,
                    "comments": s.get("descendants", 0),
                    "date": datetime.fromtimestamp(s.get("time", 0)).strftime("%Y-%m-%d")
                })
            if len(items) >= CONFIG["max_items_per_source"]:
                break
            if i % 10 == 0 and i > 0:
                time.sleep(0.5)
    except Exception as e:
        print(f"  [WARN] HN error: {e}", file=sys.stderr)

    items.sort(key=lambda x: x["score"], reverse=True)
    save_cache(ck, items)
    return items


# ============================================================
# 数据源：arXiv
# ============================================================
def fetch_arxiv(keywords):
    """抓取arXiv上AI相关的最新论文"""
    print("  Fetching arXiv...")
    ck = get_cache_key("arxiv")
    cached = load_cache(ck)
    if cached:
        return cached

    items = []
    try:
        query_terms = [quote_plus(k) for k in keywords[:6]]
        query = "+OR+".join(f"all:{t}" for t in query_terms)
        url = (
            f"http://export.arxiv.org/api/query?search_query=({query})"
            f"&sortBy=submittedDate&sortOrder=descending&maxResults=20"
        )
        xml = http_get(url)
        if not xml:
            return items

        entries = re.findall(r"<entry>(.*?)</entry>", xml, re.DOTALL)
        for entry in entries:
            title = re.search(r"<title>(.*?)</title>", entry, re.DOTALL)
            summary = re.search(r"<summary>(.*?)</summary>", entry, re.DOTALL)
            link = re.search(r'<id>(.*?)</id>', entry)
            published = re.search(r"<published>(.*?)</published>", entry)
            cats = re.findall(r'term="([^"]+)"', entry)

            if title:
                t = re.sub(r"\s+", " ", title.group(1)).strip()
                items.append({
                    "title": t,
                    "url": link.group(1).strip() if link else "",
                    "source": "arXiv",
                    "summary": re.sub(r"\s+", " ", summary.group(1)).strip()[:200] if summary else "",
                    "categories": cats[:3],
                    "date": published.group(1)[:10] if published else ""
                })
            if len(items) >= CONFIG["max_items_per_source"]:
                break
    except Exception as e:
        print(f"  [WARN] arXiv error: {e}", file=sys.stderr)

    save_cache(ck, items)
    return items


# ============================================================
# 数据源：GitHub Trending
# ============================================================
def fetch_github(keywords):
    """抓取GitHub上AI相关的热门仓库"""
    print("  Fetching GitHub Trending...")
    ck = get_cache_key("github")
    cached = load_cache(ck)
    if cached:
        return cached

    items = []
    try:
        since = "daily"
        url = f"https://api.github.com/search/repositories?q=topic:ai+topic:machine-learning&sort=stars&order=desc&per_page=15"
        xml = http_get(url, {"Accept": "application/vnd.github.v3+json"})
        if not xml:
            return items
        data = json.loads(xml)
        for repo in data.get("items", []):
            desc = repo.get("description", "") or ""
            kw_set = set(k.lower() for k in keywords)
            title = repo.get("name", "")
            text = (title + " " + desc).lower()
            if any(kw in text for kw in kw_set) or repo.get("stargazers_count", 0) > 100:
                items.append({
                    "title": f"{repo.get('full_name', title)} - {desc[:80]}",
                    "url": repo.get("html_url", ""),
                    "source": "GitHub",
                    "stars": repo.get("stargazers_count", 0),
                    "language": repo.get("language", ""),
                    "date": repo.get("updated_at", "")[:10]
                })
            if len(items) >= CONFIG["max_items_per_source"]:
                break
    except Exception as e:
        print(f"  [WARN] GitHub error: {e}", file=sys.stderr)

    items.sort(key=lambda x: x.get("stars", 0), reverse=True)
    save_cache(ck, items)
    return items


# ============================================================
# AI摘要生成（DeepSeek）
# ============================================================
def generate_ai_summary(items_by_source, keywords):
    """用DeepSeek生成AI日报摘要"""
    if not DEEPSEEK_API:
        return generate_local_summary(items_by_source, keywords)

    print("  Generating AI summary via DeepSeek...")
    all_items = []
    for source, items in items_by_source.items():
        for it in items[:8]:
            all_items.append(f"[{source}] {it['title']}")

    prompt = f"""你是一位AI领域的资深编辑。请根据今日热门AI资讯，生成一份专业的AI日报。

今日关键词: {', '.join(keywords[:8])}

今日热门资讯:
{chr(10).join(f'- {t}' for t in all_items[:25])}

请按以下格式生成日报:
1. 今日概览（100字总结今日AI领域最重要动态）
2. 重点解读（选出最重要的3条新闻，每条50-100字解读其意义）
3. 趋势洞察（总结当前AI领域的发展趋势）
4. 推荐关注（推荐2-3个值得关注的方向或项目）

用中文输出，保持专业但易读的风格。"""

    try:
        payload = json.dumps({
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "max_tokens": 1500
        }).encode("utf-8")

        req = Request(
            DEEPSEEK_URL,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {DEEPSEEK_API}"
            }
        )
        with urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"  [WARN] DeepSeek API error: {e}, using local summary", file=sys.stderr)
        return generate_local_summary(items_by_source, keywords)


def generate_local_summary(items_by_source, keywords):
    """本地生成基础摘要（无API时降级方案）"""
    print("  Generating local summary...")
    lines = []
    total = sum(len(v) for v in items_by_source.values())
    lines.append(f"### 今日概览\n")
    lines.append(f"共收集到 {total} 条AI相关资讯，覆盖 {len(items_by_source)} 个数据源。")
    lines.append(f"关键词：{', '.join(keywords[:8])}\n")

    for source, items in items_by_source.items():
        if items:
            lines.append(f"### {source} 热门 TOP3\n")
            for i, it in enumerate(items[:3], 1):
                lines.append(f"{i}. **{it['title']}**")
                if it.get("url"):
                    lines.append(f"   链接: {it['url']}")
            lines.append("")

    lines.append("### 趋势洞察\n")
    lines.append("- 大模型竞争持续白热化，开源与闭源路线并行推进")
    lines.append("- AI Agent和多模态能力成为各大厂商重点突破方向")
    lines.append("- AI安全和合规议题关注度持续上升")

    return "\n".join(lines)


# ============================================================
# Markdown报告生成
# ============================================================
def generate_markdown_report(items_by_source, summary, keywords, output_path):
    """生成完整的Markdown日报"""
    today = datetime.now().strftime("%Y年%m月%d日")
    weekday = ["周一","周二","周三","周四","周五","周六","周日"][datetime.now().weekday()]
    total = sum(len(v) for v in items_by_source.values())

    lines = []
    lines.append(f"# AI 日报 | {today} {weekday}")
    lines.append("")
    lines.append(f"> 每日AI领域精选资讯 | 关键词: {', '.join(keywords[:6])}")
    lines.append(f"> 数据来源: {', '.join(items_by_source.keys())} | 共 {total} 条")
    lines.append("")
    lines.append("---")
    lines.append("")

    # AI摘要
    lines.append("## AI 编辑摘要")
    lines.append("")
    lines.append(summary)
    lines.append("")
    lines.append("---")
    lines.append("")

    # 各来源详细列表
    for source, items in items_by_source.items():
        if not items:
            continue
        emoji = {"Hacker News": "📰", "arXiv": "📄", "GitHub": "💻"}.get(source, "📌")
        lines.append(f"## {emoji} {source}")
        lines.append("")
        for i, it in enumerate(items, 1):
            lines.append(f"### {i}. {it['title']}")
            if it.get("url"):
                lines.append(f"**链接**: {it['url']}")
            meta = []
            if it.get("score"):
                meta.append(f"热度: {it['score']}")
            if it.get("comments"):
                meta.append(f"评论: {it['comments']}")
            if it.get("stars"):
                meta.append(f"Stars: {it['stars']}")
            if it.get("language"):
                meta.append(f"语言: {it['language']}")
            if it.get("date"):
                meta.append(f"日期: {it['date']}")
            if meta:
                lines.append(f"**信息**: {' | '.join(meta)}")
            if it.get("summary"):
                lines.append(f"**摘要**: {it['summary']}")
            if it.get("categories"):
                lines.append(f"**分类**: {', '.join(it['categories'])}")
            lines.append("")

    # 页脚
    lines.append("---")
    lines.append("")
    lines.append(f"*生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
    lines.append(f"*由 AI Daily Report Generator v{VERSION} 自动生成*")

    content = "\n".join(lines)
    Path(output_path).write_text(content, encoding="utf-8")
    return content


# ============================================================
# 命令处理
# ============================================================
def cmd_generate(args):
    """生成日报"""
    keywords = args.keywords.split(",") if args.keywords else CONFIG["default_keywords"]
    if args.cn:
        keywords = CONFIG["cn_keywords"] + keywords
    sources = args.sources.split(",") if args.sources else CONFIG["default_sources"]
    output = args.output or f"ai_daily_{datetime.now().strftime('%Y%m%d')}.md"

    print(f"\n{'='*50}")
    print(f"  AI Daily Report Generator v{VERSION}")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*50}\n")

    # 抓取数据
    items_by_source = {}
    fetchers = {
        "hackernews": ("Hacker News", fetch_hackernews),
        "arxiv": ("arXiv", fetch_arxiv),
        "github": ("GitHub", fetch_github),
    }
    for src in sources:
        if src in fetchers:
            name, fn = fetchers[src]
            items = fn(keywords)
            items_by_source[name] = items
            print(f"  {name}: {len(items)} items")

    if not any(items_by_source.values()):
        print("[ERROR] No data fetched. Check network connection.")
        return

    # 生成AI摘要
    summary = generate_ai_summary(items_by_source, keywords)

    # 生成报告
    out_path = Path(output)
    content = generate_markdown_report(items_by_source, summary, keywords, out_path)
    total = sum(len(v) for v in items_by_source.values())

    print(f"\n{'='*50}")
    print(f"  Report generated: {out_path}")
    print(f"  Total items: {total}")
    print(f"  File size: {len(content):,} chars")
    print(f"{'='*50}\n")


def cmd_preview(args):
    """预览今日数据"""
    keywords = args.keywords.split(",") if args.keywords else CONFIG["default_keywords"]
    sources = args.sources.split(",") if args.sources else CONFIG["default_sources"]

    print(f"\n  AI Daily Report - Data Preview\n")
    fetchers = {
        "hackernews": ("Hacker News", fetch_hackernews),
        "arxiv": ("arXiv", fetch_arxiv),
        "github": ("GitHub", fetch_github),
    }
    for src in sources:
        if src in fetchers:
            name, fn = fetchers[src]
            items = fn(keywords)
            print(f"  [{name}] {len(items)} items:")
            for it in items[:5]:
                print(f"    - {it['title'][:60]}")
            print()


def cmd_stats(args):
    """统计缓存信息"""
    cache_dir = CONFIG["cache_dir"]
    if not cache_dir.exists():
        print("  No cache data")
        return
    files = list(cache_dir.glob("*.json"))
    total_size = sum(f.stat().st_size for f in files)
    print(f"\n  Cache: {len(files)} files, {total_size/1024:.1f} KB")
    for f in sorted(files):
        age = (time.time() - f.stat().st_mtime) / 60
        print(f"    {f.name} ({age:.0f}min ago)")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="AI Daily Report Generator - AI日报生成器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python ai_daily_report.py generate                    # 默认生成
  python ai_daily_report.py generate -k "LLM,agent"    # 指定关键词
  python ai_daily_report.py generate --cn               # 含中文关键词
  python ai_daily_report.py generate -s "hackernews,arxiv"  # 指定来源
  python ai_daily_report.py generate -o report.md       # 指定输出
  python ai_daily_report.py preview                     # 预览数据
  python ai_daily_report.py stats                       # 缓存统计
        """
    )
    sub = parser.add_subparsers(dest="command")

    # generate
    p = sub.add_parser("generate", help="生成AI日报")
    p.add_argument("-k", "--keywords", help="关键词，逗号分隔")
    p.add_argument("--cn", action="store_true", help="包含中文关键词")
    p.add_argument("-s", "--sources", help="数据源: hackernews,arxiv,github")
    p.add_argument("-o", "--output", help="输出文件路径")
    p.set_defaults(func=cmd_generate)

    # preview
    p = sub.add_parser("preview", help="预览数据")
    p.add_argument("-k", "--keywords", help="关键词")
    p.add_argument("-s", "--sources", help="数据源")
    p.set_defaults(func=cmd_preview)

    # stats
    p = sub.add_parser("stats", help="缓存统计")
    p.add_argument("--clean", action="store_true", help="清除缓存")
    p.set_defaults(func=cmd_stats)

    args = parser.parse_args()
    if not args.command:
        args = parser.parse_args(["generate"])
    args.func(args)


if __name__ == "__main__":
    main()
