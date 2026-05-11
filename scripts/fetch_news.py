#!/usr/bin/env python3
"""Fetch daily hot news from multiple sources and output as social card batch config."""

import json
import argparse
import os
import sys
from datetime import datetime, timedelta

TODAY = datetime.now().strftime("%Y-%m-%d")


def fetch_hackernews(top_n=5):
    """Fetch top stories from Hacker News."""
    import urllib.request
    stories = []
    try:
        url = "https://hacker-news.firebaseio.com/v0/topstories.json"
        req = urllib.request.Request(url, headers={"User-Agent": "DailyDigest/1.0"})
        ids = json.loads(urllib.request.urlopen(req, timeout=15).read())[:top_n * 2]

        for sid in ids:
            if len(stories) >= top_n:
                break
            item_url = f"https://hacker-news.firebaseio.com/v0/item/{sid}.json"
            req = urllib.request.Request(item_url, headers={"User-Agent": "DailyDigest/1.0"})
            item = json.loads(urllib.request.urlopen(req, timeout=10).read())
            if item.get("type") == "story" and item.get("score", 0) > 50:
                title = item.get("title", "")
                score = item.get("score", 0)
                link = item.get("url", f"https://news.ycombinator.com/item?id={sid}")
                desc = item.get("text", "")
                if desc:
                    import re
                    desc = re.sub(r'<[^>]+>', '', desc)[:150].strip()
                stories.append({
                    "title": title,
                    "body": f"HN Score: {score}" + (f" | {desc}" if desc else ""),
                    "source": "Hacker News",
                    "url": link,
                })
    except Exception as e:
        print(f"[WARN] Hacker News fetch failed: {e}", file=sys.stderr)
    return stories


def fetch_github_trending(top_n=5):
    """Fetch trending repos from GitHub search API."""
    import urllib.request
    repos = []
    try:
        date_since = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        url = f"https://api.github.com/search/repositories?q=created:>{date_since}&sort=stars&order=desc&per_page={top_n}"
        req = urllib.request.Request(url, headers={
            "User-Agent": "DailyDigest/1.0",
            "Accept": "application/vnd.github.v3+json",
        })
        data = json.loads(urllib.request.urlopen(req, timeout=15).read())

        for repo in data.get("items", []):
            full_name = repo.get("full_name", "")
            desc = (repo.get("description") or "")[:120]
            stars = repo.get("stargazers_count", 0)
            lang = repo.get("language", "")
            html_url = repo.get("html_url", "")
            repos.append({
                "title": full_name,
                "body": (f"[{lang}] " if lang else "") + (f"{desc} | ★{stars}" if desc else f"★{stars}"),
                "source": "GitHub Trending",
                "url": html_url,
            })
    except Exception as e:
        print(f"[WARN] GitHub Trending fetch failed: {e}", file=sys.stderr)
    return repos


def fetch_producthunt(top_n=3):
    """Fetch top posts from Product Hunt via their weekly RSS."""
    import urllib.request
    items = []
    try:
        import xml.etree.ElementTree as ET
        url = "https://www.producthunt.com/feed"
        req = urllib.request.Request(url, headers={"User-Agent": "DailyDigest/1.0"})
        raw = urllib.request.urlopen(req, timeout=15).read()
        root = ET.fromstring(raw)

        for item in root.findall(".//item")[:top_n]:
            title_el = item.find("title")
            link_el = item.find("link")
            desc_el = item.find("description")
            title = title_el.text if title_el is not None else ""
            link = link_el.text if link_el is not None else ""
            desc = ""
            if desc_el is not None and desc_el.text:
                import re
                desc = re.sub(r'<[^>]+>', '', desc_el.text)[:120].strip()
            items.append({
                "title": title,
                "body": desc,
                "source": "Product Hunt",
                "url": link,
            })
    except Exception as e:
        print(f"[WARN] Product Hunt fetch failed: {e}", file=sys.stderr)
    return items


SOURCE_COLORS = {
    "Hacker News": "FF6600",
    "GitHub Trending": "6E40C9",
    "Product Hunt": "DA552F",
}


def generate_config(news_items, output_path):
    cards = []
    for i, item in enumerate(news_items):
        source = item.get("source", "")
        cards.append({
            "title": item["title"],
            "body": item.get("body", ""),
            "caption": f"来源: {source} | {item.get('url', '')}",
            "output": f"card_{i+1:02d}.png",
            "accent": SOURCE_COLORS.get(source, "6366F1"),
        })

    config = {
        "date": TODAY,
        "defaults": {"width": 1080, "height": 1080, "alpha": 160},
        "cards": cards,
    }

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    print(f"Config: {output_path} ({len(cards)} cards)")
    return config


def generate_readme(config, output_path):
    """Generate a README.md with today's digest."""
    lines = [
        f"# Daily Tech Digest — {config['date']}",
        "",
        f"Auto-generated tech news cards, updated daily.",
        "",
        f"## {config['date']} Top Stories",
        "",
    ]
    for i, card in enumerate(config["cards"]):
        lines.append(f"{i+1}. **{card['title']}**")
        if card.get("body"):
            lines.append(f"   {card['body'][:100]}")
        lines.append("")

    lines.append("---")
    lines.append("*Generated by [daily-tech-digest](https://github.com/QiyuanY/daily-tech-digest)*")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"README: {output_path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sources", default="all", help="hn,github,producthunt or all")
    parser.add_argument("--top", type=int, default=5)
    parser.add_argument("--config-out", default="news_config.json")
    parser.add_argument("--readme-out", default="")
    args = parser.parse_args()

    fetchers = {
        "hn": ("Hacker News", fetch_hackernews),
        "github": ("GitHub Trending", fetch_github_trending),
        "producthunt": ("Product Hunt", fetch_producthunt),
    }

    selected = list(fetchers.keys()) if args.sources == "all" else [s.strip() for s in args.sources.split(",")]
    all_news = []

    for key in selected:
        if key not in fetchers:
            continue
        name, fn = fetchers[key]
        print(f"Fetching {name}...")
        items = fn(args.top)
        for item in items:
            item["source"] = name
        all_news.extend(items)
        print(f"  → {len(items)} items")

    if not all_news:
        print("No news fetched.", file=sys.stderr)
        sys.exit(1)

    config = generate_config(all_news, args.config_out)

    if args.readme_out:
        generate_readme(config, args.readme_out)


if __name__ == "__main__":
    main()
