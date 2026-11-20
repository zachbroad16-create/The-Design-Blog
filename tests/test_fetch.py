"""Run with: python3 tests/test_fetch.py"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import fetch_feeds as f  # noqa: E402

items, used = f.fetch_source({"name": "Fixture", "tags": [], "feeds": [str(ROOT / "tests" / "fixture_feed.xml")]})
assert used and len(items) == 2, items
lamp, studio = items
assert lamp["image"] == "https://example.com/lamp.jpg"
assert "appeared first" not in lamp["summary"], lamp["summary"]
assert {"products", "materials"} <= set(lamp["categories"]), lamp["categories"]
assert studio["image"] == "https://example.com/studio.jpg"
assert "companies" in studio["categories"]
assert f.categorise("Card games", "nothing here", []) == []
print("ok")
