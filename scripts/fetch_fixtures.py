"""One-off helper: fetch Aetherhub pages we need as test fixtures.

Uses curl_cffi with a Chrome TLS fingerprint so Cloudflare treats it as a
real browser. Not part of the runtime pipeline — only run when re-capturing
fixtures. Intentionally kept outside scrapers/ so it isn't imported by tests.
"""
from __future__ import annotations

import sys
from pathlib import Path

from curl_cffi import requests as ccr

TARGETS = [
    (
        "tests/fixtures/aetherhub_historic_brawl_meta.html",
        "https://aetherhub.com/Metagame/Historic-Brawl/",
    ),
    (
        "tests/fixtures/aetherhub_brawl_deck.html",
        "https://aetherhub.com/Metagame/Historic-Brawl/Deck/hei-bai-forest-guardian-1414259",
    ),
    (
        "tests/fixtures/aetherhub_standard_bo3_deck.html",
        # First Traditional-Standard (BO3) deck slug is filled in below after we
        # discover it — see main().
        "",
    ),
]


def fetch(url: str) -> str:
    resp = ccr.get(url, impersonate="chrome124", timeout=30)
    resp.raise_for_status()
    return resp.text


def discover_first_bo3_deck() -> str:
    """Find the first archetype deck URL on the Traditional-Standard tier list."""
    from selectolax.parser import HTMLParser

    html = fetch("https://aetherhub.com/Metagame/Traditional-Standard/")
    tree = HTMLParser(html)
    for a in tree.css("a.ae-decklink"):
        href = a.attributes.get("href") or ""
        if "/Metagame/Traditional-Standard/Deck/" in href:
            return "https://aetherhub.com" + href
    raise RuntimeError("no Traditional-Standard deck link found")


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    (root / "tests" / "fixtures").mkdir(parents=True, exist_ok=True)

    # Fill in the BO3 deck URL by discovering it live.
    targets = list(TARGETS)
    if not targets[2][1]:
        bo3_url = discover_first_bo3_deck()
        print(f"[info] discovered Traditional-Standard deck: {bo3_url}")
        targets[2] = (targets[2][0], bo3_url)

    for rel_path, url in targets:
        out = root / rel_path
        print(f"[fetch] {url} -> {rel_path}")
        html = fetch(url)
        out.write_text(html, encoding="utf-8")
        print(f"[ok] wrote {len(html):,} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
