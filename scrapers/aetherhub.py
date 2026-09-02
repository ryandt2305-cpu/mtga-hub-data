"""Aetherhub tier list + decklist scraper.

Selectors are derived from real fixture pages captured 2026-09; see
tests/fixtures/. If Aetherhub reworks their markup, re-run
scripts/fetch_fixtures.py to refresh the fixtures, adjust selectors, and
re-run pytest to confirm.

Cloudflare notes: Aetherhub sits behind Cloudflare but does not challenge
a Chrome-fingerprinted TLS handshake, so curl_cffi with impersonate=
'chrome124' works without a headless browser.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from selectolax.parser import HTMLParser

AETHERHUB_BASE = "https://aetherhub.com"
WUBRGC = {"W", "U", "B", "R", "G", "C"}


@dataclass
class Archetype:
    name: str
    meta_share: float
    colors: list[str] = field(default_factory=list)
    decklist_url: str = ""
    sample_count: int | None = None


@dataclass
class CardEntry:
    name: str
    quantity: int
    role: str  # "commander" | "mainboard" | "sideboard"


def _absolutize(href: str) -> str:
    if not href:
        return ""
    if href.startswith("http://") or href.startswith("https://"):
        return href
    if href.startswith("/"):
        return AETHERHUB_BASE + href
    return AETHERHUB_BASE + "/" + href


def _parse_meta_share(text: str) -> float | None:
    """'4.00% of Metagame' -> 0.04"""
    if not text:
        return None
    frag = text.strip().split("%", 1)[0]
    try:
        return float(frag) / 100.0
    except ValueError:
        return None


def _parse_sample_count(text: str) -> int | None:
    """'3119 matches' -> 3119"""
    if not text:
        return None
    frag = text.strip().split(None, 1)[0]
    frag = frag.replace(",", "")
    try:
        return int(frag)
    except ValueError:
        return None


def _colors_from_progress_bar(row) -> list[str]:
    """Aetherhub sets the color combo as the trailing class token on the
    progress-bar div (e.g. 'progress-bar faded wubg'). Split into WUBRGC
    letters, in canonical WUBRG order."""
    bar = row.css_first(".progress-bar")
    if bar is None:
        return []
    cls = (bar.attributes.get("class") or "").strip()
    if not cls:
        return []
    tokens = cls.split()
    # The color combo is the last token that consists only of wubrgc letters.
    combo = ""
    for tok in reversed(tokens):
        low = tok.lower()
        if low and all(ch in "wubrgc" for ch in low):
            combo = low
            break
    if not combo:
        return []
    seen: list[str] = []
    for ch in combo:
        u = ch.upper()
        if u in WUBRGC and u not in seen:
            seen.append(u)
    return seen


def parse_tier_list(html: str) -> list[Archetype]:
    tree = HTMLParser(html)
    archetypes: list[Archetype] = []
    for row in tree.css("tbody.ae-tbody-deckrow"):
        title_a = row.css_first(".ae-decktitle a")
        share_span = row.css_first(".percent-metagame")
        if title_a is None or share_span is None:
            continue
        name = (title_a.text() or "").strip()
        meta_share = _parse_meta_share(share_span.text() or "")
        if not name or meta_share is None:
            continue
        link = row.css_first("a.ae-decklink")
        decklist_url = _absolutize(link.attributes.get("href", "") if link else "")
        if not decklist_url:
            # Fall back to the title anchor's href.
            decklist_url = _absolutize(title_a.attributes.get("href", ""))
        matches_node = row.css_first(".ae-deckmatches")
        sample_count = _parse_sample_count(matches_node.text() if matches_node else "")
        colors = _colors_from_progress_bar(row)
        archetypes.append(
            Archetype(
                name=name,
                meta_share=meta_share,
                colors=colors,
                decklist_url=decklist_url,
                sample_count=sample_count,
            )
        )
    return archetypes


_SECTION_PREFIXES = (
    ("commander", "commander"),
    ("main", "mainboard"),
    ("side", "sideboard"),
)


def _classify_section(header_text: str) -> str | None:
    low = header_text.strip().lower()
    for prefix, role in _SECTION_PREFIXES:
        if low.startswith(prefix):
            return role
    return None


def parse_decklist(html: str) -> list[CardEntry]:
    """Parse the visual pane of an Aetherhub deck page.

    Section boundaries are <h5> headers whose text starts with 'Commander',
    'Main', or 'Side'. Each copy of a card is rendered as its own
    <a class="cardLink" data-card-name="..."> anchor; quantity per card is
    the count of anchors in that section with the same data-card-name.
    """
    tree = HTMLParser(html)
    pane = None
    for div in tree.css('div[id^="tab_visual_"]'):
        pane = div
        break
    if pane is None:
        return []

    # Walk descendants in document order. h5 updates the current section;
    # each a.cardLink[data-card-name] increments the count for its section.
    counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    current_section: str | None = None
    for node in pane.css("*"):
        if node.tag == "h5":
            role = _classify_section(node.text() or "")
            if role is not None:
                current_section = role
            continue
        if node.tag != "a":
            continue
        cls = node.attributes.get("class") or ""
        if "cardLink" not in cls:
            continue
        card_name = node.attributes.get("data-card-name")
        if not card_name or current_section is None:
            continue
        counts[current_section][card_name] += 1

    out: list[CardEntry] = []
    for role in ("commander", "mainboard", "sideboard"):
        if role not in counts:
            continue
        for card_name, qty in counts[role].items():
            out.append(CardEntry(name=card_name, quantity=qty, role=role))
    return out


def fetch_tier_list_html(url_path: str) -> str:
    """Fetch a tier-list page. url_path is the Aetherhub URL slug after the
    base (e.g. 'Historic-Brawl', 'Traditional-Standard'). Kept as a thin
    fetch wrapper so tests can exercise parse_tier_list against fixtures
    without touching the network.
    """
    from curl_cffi import requests as ccr

    url = f"{AETHERHUB_BASE}/Metagame/{url_path}/"
    resp = ccr.get(url, impersonate="chrome124", timeout=30)
    resp.raise_for_status()
    return resp.text


def fetch_tier_list(url_path: str) -> list[Archetype]:
    return parse_tier_list(fetch_tier_list_html(url_path))


def fetch_decklist(url: str) -> list[CardEntry]:
    from curl_cffi import requests as ccr

    resp = ccr.get(url, impersonate="chrome124", timeout=30)
    resp.raise_for_status()
    return parse_decklist(resp.text)
