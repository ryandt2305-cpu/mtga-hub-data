from unittest.mock import patch

from scrapers.aetherhub import Archetype, CardEntry
from scripts.build_meta import build

FAKE_ARCHETYPES = [
    Archetype(
        name=f"Archetype {i}",
        meta_share=0.10 - i * 0.01,
        colors=["U"],
        decklist_url=f"https://aetherhub.com/Metagame/Historic-Brawl/Deck/example-{i}",
        sample_count=100 + i,
    )
    for i in range(5)
]

FAKE_DECKLIST = [
    CardEntry(name="Commander", quantity=1, role="commander"),
    *[CardEntry(name=f"Card {i}", quantity=1, role="mainboard") for i in range(99)],
]

FAKE_BO3_DECKLIST = [
    *[CardEntry(name=f"Main {i}", quantity=1, role="mainboard") for i in range(60)],
    *[CardEntry(name=f"Side {i}", quantity=1, role="sideboard") for i in range(15)],
]


def test_build_produces_schema_v1_snapshot():
    with patch("scripts.build_meta.fetch_tier_list", return_value=FAKE_ARCHETYPES), \
         patch("scripts.build_meta.fetch_decklist", return_value=FAKE_DECKLIST):
        snap = build()
    assert snap["schema_version"] == 1
    assert "brawl100" in snap["formats"]
    # 5 archetypes returned, all under TOP_N_DECKLISTS_PER_FORMAT (10), so all appear.
    assert len(snap["formats"]["brawl100"]["archetypes"]) == 5


def test_build_survives_per_format_scraper_error():
    def raise_for_traditional_standard(fmt_key: str):
        if fmt_key == "Traditional-Standard":
            raise RuntimeError("simulated")
        return FAKE_ARCHETYPES

    with patch(
        "scripts.build_meta.fetch_tier_list",
        side_effect=raise_for_traditional_standard,
    ), patch("scripts.build_meta.fetch_decklist", return_value=FAKE_DECKLIST):
        snap = build()
    assert snap["formats"]["standard_bo3"]["archetypes"] == []
    assert len(snap["formats"]["brawl100"]["archetypes"]) == 5


def test_build_strips_sideboard_from_bo1_formats():
    """standard_bo1 has expect_sideboard=False. Even if the decklist scraper
    accidentally returns sideboard rows, build() must drop them from the
    published snapshot."""
    with patch("scripts.build_meta.fetch_tier_list", return_value=FAKE_ARCHETYPES), \
         patch("scripts.build_meta.fetch_decklist", return_value=FAKE_BO3_DECKLIST):
        snap = build()
    bo1_first = snap["formats"]["standard_bo1"]["archetypes"][0]
    roles = {entry["role"] for entry in bo1_first["decklist"]}
    assert "sideboard" not in roles

    bo3_first = snap["formats"]["standard_bo3"]["archetypes"][0]
    bo3_roles = {entry["role"] for entry in bo3_first["decklist"]}
    assert "sideboard" in bo3_roles


def test_build_uses_snapshot_keys_the_rust_client_expects():
    """format_to_snapshot_key in mtga-tool maps Brawl100→brawl100 and
    StandardBrawl60→standardbrawl60. Break-glass check that we didn't
    rename them on the aggregator side."""
    with patch("scripts.build_meta.fetch_tier_list", return_value=FAKE_ARCHETYPES), \
         patch("scripts.build_meta.fetch_decklist", return_value=FAKE_DECKLIST):
        snap = build()
    for required in ("brawl100", "standardbrawl60"):
        assert required in snap["formats"], f"missing snapshot key {required}"
