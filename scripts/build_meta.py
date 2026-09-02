"""Build meta.json by scraping Aetherhub for every supported format,
validating the result, and writing it to data/meta.json.

Run: python -m scripts.build_meta
Exit code 0 on success, non-zero on validation failure.
"""
from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from scrapers.aetherhub import (
    AETHERHUB_BASE,
    Archetype,
    CardEntry,
    fetch_decklist,
    fetch_tier_list,
)
from validators.meta import validate

# Per-format table: (snapshot_key, aetherhub_url_path, expect_sideboard).
# snapshot_key matches the client's format_to_snapshot_key mapping in
# mtga-tool:src-tauri/src/services/deck/meta.rs.
# aetherhub_url_path is the Aetherhub URL slug after /Metagame/.
# expect_sideboard drives a post-parse cleanup so BO1 decks never publish
# stray sideboard rows (Aetherhub's markup shouldn't include them for BO1,
# but the safety cushion keeps a source-side change from breaking the shape).
FORMAT_MAPPINGS: list[tuple[str, str, bool]] = [
    ("brawl100",         "Historic-Brawl",         False),
    ("standardbrawl60",  "Brawl",                  False),
    ("standard_bo1",     "Standard-BO1",           False),
    ("standard_bo3",     "Traditional-Standard",   True),
    ("historic_bo1",     "Historic-BO1",           False),
    ("historic_bo3",     "Traditional-Historic",   True),
    ("explorer_bo1",     "Explorer-BO1",           False),
    ("explorer_bo3",     "Traditional-Explorer",   True),
    ("timeless_bo1",     "Timeless",               False),
    ("timeless_bo3",     "Traditional-Timeless",   True),
    ("alchemy_bo1",      "Alchemy-BO1",            False),
    ("alchemy_bo3",      "Traditional-Alchemy",    True),
]

TOP_N_DECKLISTS_PER_FORMAT = 10


def _iso_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _decklist_to_entries(cards: list[CardEntry]) -> list[dict]:
    return [{"name": c.name, "quantity": c.quantity, "role": c.role} for c in cards]


def _archetype_to_dict(a: Archetype, decklist: list[CardEntry] | None) -> dict:
    return {
        "name": a.name,
        "meta_share": a.meta_share,
        "sample_count": a.sample_count,
        "colors": a.colors,
        "representative_decklist_url": a.decklist_url,
        "decklist": _decklist_to_entries(decklist) if decklist else [],
    }


def build() -> dict:
    now = _iso_now()
    formats_dict: dict = {}
    for snapshot_key, aether_key, expect_sideboard in FORMAT_MAPPINGS:
        try:
            archetypes = fetch_tier_list(aether_key)
        except Exception as e:  # noqa: BLE001 — we want ANY exception to degrade gracefully
            print(f"[warn] tier list {aether_key} failed: {e}", file=sys.stderr)
            formats_dict[snapshot_key] = {
                "aetherhub_format_key": aether_key,
                "single_source": True,
                "sample_size": None,
                "sample_window_days": None,
                "archetypes": [],
            }
            continue

        top = archetypes[:TOP_N_DECKLISTS_PER_FORMAT]
        archetype_dicts = []
        for arch in top:
            decklist: list[CardEntry] | None = None
            if arch.decklist_url:
                try:
                    decklist = fetch_decklist(arch.decklist_url)
                    if not expect_sideboard and decklist:
                        # BO1 pages should never emit sideboard rows, but if
                        # markup drifts, discard stray sideboard entries
                        # rather than publish a broken shape.
                        decklist = [c for c in decklist if c.role != "sideboard"]
                except Exception as e:  # noqa: BLE001
                    print(f"[warn] deck {arch.decklist_url} failed: {e}", file=sys.stderr)
            archetype_dicts.append(_archetype_to_dict(arch, decklist))
        # Include tail archetypes without decklists — meta share is still useful.
        for arch in archetypes[TOP_N_DECKLISTS_PER_FORMAT:]:
            archetype_dicts.append(_archetype_to_dict(arch, None))

        formats_dict[snapshot_key] = {
            "aetherhub_format_key": aether_key,
            "single_source": True,
            "sample_size": None,
            "sample_window_days": None,
            "archetypes": archetype_dicts,
        }

    return {
        "schema_version": 1,
        "generated_at": now,
        "sources": [
            {"name": "aetherhub", "url": f"{AETHERHUB_BASE}/Metagame/", "fetched_at": now},
        ],
        "formats": formats_dict,
    }


def main() -> int:
    snapshot = build()
    ok, warnings = validate(snapshot)
    for w in warnings:
        print(f"[warn] {w}", file=sys.stderr)
    if not ok:
        print("[error] validation failed", file=sys.stderr)
        return 1
    out_path = Path("data/meta.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2, sort_keys=True)
    print(f"[ok] wrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
