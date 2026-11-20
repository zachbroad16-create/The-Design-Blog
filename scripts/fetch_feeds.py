#!/usr/bin/env python3
"""Pull industrial design RSS feeds and write data/articles.json.

Runs on a schedule in GitHub Actions. New stories are merged with the
existing file, so one feed being down never empties the site.
"""
from __future__ import annotations

import html
import json
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import feedparser

ROOT = Path(__file__).resolve().parent.parent
SOURCES_FILE = ROOT / "scripts" / "sources.json"
OUT_FILE = ROOT / "data" / "articles.json"

MAX_AGE_DAYS = 60
MAX_ITEMS = 900
# A feed URL we haven't read before gets this many pages read, to fill in the
# last few weeks. After that, each run only reads its first page.
BACKFILL_PAGES = 8
SUMMARY_WORDS = 38
USER_AGENT = "Mozilla/5.0 (compatible; DesignBlogFeedReader/1.0)"

# Keyword rules for the category tabs. A story can sit in several.
# Keyword rules for the category tabs. A story can sit in several.
# Words match whole words; a trailing * matches any ending (recycl* -> recycled).
CATEGORIES = {
    "automotive": [
        "car", "cars", "concept car*", "supercar*", "hypercar*", "sports car*",
        "race car*", "automotive", "automaker*", "carmaker*", "vehicle*", "ev", "evs",
        "electric vehicle*", "suv", "suvs", "pickup*", "motorcycle*", "motorbike*",
        "e-bike*", "scooter*", "livery", "f1", "formula 1", "formula one",
        "porsche", "ferrari", "lamborghini", "bmw", "mercedes*", "audi", "volkswagen",
        "polestar", "tesla", "rivian", "lucid motors", "hyundai", "kia", "toyota",
        "lexus", "honda", "nissan", "mazda", "cadillac", "aston martin", "bentley",
        "rolls-royce", "mclaren", "lotus cars", "volvo", "fiat", "alfa romeo", "renault",
        "peugeot", "citroën", "citroen", "jaguar", "land rover", "range rover", "infiniti",
        "ducati", "bugatti", "pagani", "koenigsegg", "maserati", "lancia", "byd",
    ],
    "products": [
        "product*", "launch*", "lamp*", "lighting", "chair*", "stool*", "table*",
        "sofa*", "furniture", "speaker*", "headphone*", "earbud*", "watch*",
        "camera*", "phone*", "smartphone*", "kettle*", "appliance*", "gadget*",
        "device*", "tool*", "bike*", "bicycle*", "e-bike*", "scooter*", "car", "cars",
        "vehicle*", "knife", "knives", "bag*", "backpack*", "shoe*", "sneaker*",
        "keyboard*", "kitchen*", "toy*", "unveil*", "edc", "wearable*", "drone*",
    ],
    "materials": [
        "material*", "mycelium", "bioplastic*", "plastic*", "recycl*", "alumin*",
        "steel", "titanium", "carbon fibre", "carbon fiber", "wood*", "timber",
        "cork", "bamboo", "ceramic*", "glass", "concrete", "textile*", "fabric*",
        "leather", "biomaterial*", "bio-based", "composite*", "3d print*",
        "3d-print*", "additive manufactur*", "injection mo*", "cnc",
        "manufactur*", "upcycl*", "circular", "waste", "sustainab*", "algae",
    ],
    "styles": [
        "trend*", "style*", "aesthetic*", "colour*", "color*", "minimal*",
        "brutalis*", "brutalist", "retro", "nostalg*", "y2k", "postmodern*",
        "bauhaus", "sculptural", "translucent", "exhibition*", "milan design week",
        "salone", "design week", "collection*", "concept*", "futuris*",
    ],
    "companies": [
        "studio*", "brand*", "compan*", "startup*", "founder*", "acquir*",
        "partner*", "collaborat*", "ikea", "vitra", "muji", "teenage engineering",
        "dyson", "apple", "braun", "bang & olufsen", "herman miller", "interview*",
        "award*", "red dot", "if design", "designer*", "ceo",
    ],
}


def _compile(words: list[str]) -> re.Pattern:
    parts = []
    for word in words:
        if word.endswith("*"):
            parts.append(r"\b" + re.escape(word[:-1]))
        else:
            parts.append(r"\b" + re.escape(word) + r"\b")
    return re.compile("|".join(parts), re.I)


CATEGORY_PATTERNS = {name: _compile(words) for name, words in CATEGORIES.items()}

IMG_RE = re.compile(r"<img[^>]+src=[\"']([^\"']+)[\"']", re.I)
TAG_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"\s+")


def clean_text(raw: str) -> str:
    text = TAG_RE.sub(" ", raw or "")
    text = html.unescape(text)
    return WS_RE.sub(" ", text).strip()


def summarise(raw: str) -> str:
    words = clean_text(raw).split(" ")
    # Drop common feed boilerplate like "The post X appeared first on Y."
    joined = " ".join(words)
    joined = re.sub(r"The post .* appeared first on .*$", "", joined).strip()
    words = joined.split(" ")
    if len(words) <= SUMMARY_WORDS:
        return joined
    return " ".join(words[:SUMMARY_WORDS]).rstrip(",.;:") + "…"


def find_image(entry) -> str | None:
    for key in ("media_content", "media_thumbnail"):
        for media in entry.get(key, []) or []:
            url = media.get("url")
            if url and media.get("medium", "image") == "image":
                return url
    for link in entry.get("links", []) or []:
        if link.get("rel") == "enclosure" and str(link.get("type", "")).startswith("image"):
            return link.get("href")
    for block in entry.get("content", []) or []:
        match = IMG_RE.search(block.get("value", ""))
        if match:
            return match.group(1)
    match = IMG_RE.search(entry.get("summary", "") or "")
    if match:
        return match.group(1)
    return None


def published(entry) -> str:
    for key in ("published_parsed", "updated_parsed"):
        value = entry.get(key)
        if value:
            return datetime.fromtimestamp(time.mktime(value), tz=timezone.utc).isoformat()
    return datetime.now(timezone.utc).isoformat()


def categorise(title: str, summary: str, source_tags: list[str]) -> list[str]:
    hay = f"{title} {summary}"
    found = [name for name, pattern in CATEGORY_PATTERNS.items() if pattern.search(hay)]
    for tag in source_tags:
        if tag not in found:
            found.append(tag)
    return found


def read_feed(url: str):
    try:
        parsed = feedparser.parse(url, agent=USER_AGENT)
    except Exception as exc:  # network errors, bad XML
        print(f"  ! {url}: {exc}", file=sys.stderr)
        return None
    if not parsed.entries:
        status = getattr(parsed, "status", "?")
        print(f"  ! {url}: no entries (HTTP {status})", file=sys.stderr)
        return None
    return parsed


def page_url(url: str, page: int) -> str:
    """WordPress feeds serve older posts at ?paged=N."""
    return f"{url}{'&' if '?' in url else '?'}paged={page}"


def fetch_feed(url: str, source: dict, backfilled: set[str]) -> list[dict]:
    pages = 1 if url in backfilled else BACKFILL_PAGES
    if pages > 1:
        print(f"  backfilling {url} (up to {pages} pages)")
    parsed = read_feed(url)
    if parsed is None:
        return []
    items = to_items(parsed.entries, source)
    seen = {i["id"] for i in items}
    for page in range(2, pages + 1):
        older = read_feed(page_url(url, page))
        if older is None:
            break
        new = [i for i in to_items(older.entries, source) if i["id"] not in seen]
        if not new:  # feed ignores ?paged, or we've run out
            break
        items += new
        seen.update(i["id"] for i in new)
    backfilled.add(url)
    return items


def fetch_source(source: dict, backfilled: set[str] | None = None) -> tuple[list[dict], str | None]:
    """Return a source's stories and which feed(s) answered.

    By default the feeds list is fallbacks, tried in order until one works.
    With "combine": true, every feed in the list is read and merged
    (for example a site's design and technology sections).
    """
    if backfilled is None:
        backfilled = set()
    if source.get("combine"):
        items, used = [], []
        for url in source["feeds"]:
            got = fetch_feed(url, source, backfilled)
            if got:
                items += got
                used.append(url)
        return items, ", ".join(used) or None
    for url in source["feeds"]:
        items = fetch_feed(url, source, backfilled)
        if items:
            return items, url
    return [], None


def to_items(entries, source: dict) -> list[dict]:
        items = []
        for entry in entries:
            link = entry.get("link")
            title = clean_text(entry.get("title", ""))
            if not link or not title:
                continue
            raw = entry.get("summary", "")
            if not raw and entry.get("content"):
                raw = entry["content"][0].get("value", "")
            summary = summarise(raw)
            items.append({
                "id": link,
                "title": title,
                "link": link,
                "summary": summary,
                "image": find_image(entry),
                "source": source["name"],
                "published": published(entry),
                "categories": categorise(title, summary, source.get("tags", [])),
            })
        return items


def main() -> int:
    sources = json.loads(SOURCES_FILE.read_text())
    existing = {}
    backfilled: set[str] = set()
    if OUT_FILE.exists():
        try:
            previous = json.loads(OUT_FILE.read_text())
            backfilled = set(previous.get("backfilled", []))
            for item in previous.get("articles", []):
                existing[item["id"]] = item
        except (json.JSONDecodeError, KeyError):
            print("! existing articles.json unreadable, starting fresh", file=sys.stderr)

    tags_by_source = {s["name"]: s.get("tags", []) for s in sources}
    # Re-tag stored stories so new keyword rules apply to them too.
    for item in existing.values():
        item["categories"] = categorise(
            item["title"], item.get("summary", ""), tags_by_source.get(item["source"], []))

    status = []
    for source in sources:
        print(f"- {source['name']}")
        items, used = fetch_source(source, backfilled)
        status.append({"name": source["name"], "ok": bool(items), "count": len(items)})
        for item in items:
            existing[item["id"]] = item  # newer copy wins

    cutoff = datetime.now(timezone.utc) - timedelta(days=MAX_AGE_DAYS)
    articles = [
        a for a in existing.values()
        if datetime.fromisoformat(a["published"]) >= cutoff
    ]
    articles.sort(key=lambda a: a["published"], reverse=True)
    articles = articles[:MAX_ITEMS]

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(json.dumps({
        "updated": datetime.now(timezone.utc).isoformat(),
        "sources": status,
        "backfilled": sorted(backfilled),
        "articles": articles,
    }, indent=1, ensure_ascii=False) + "\n")

    ok = sum(1 for s in status if s["ok"])
    print(f"{len(articles)} stories kept; {ok}/{len(status)} sources responded")
    # Fail the job only if every source failed, so one dead feed doesn't block deploys.
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
