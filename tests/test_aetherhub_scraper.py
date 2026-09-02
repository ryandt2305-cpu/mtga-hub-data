from pathlib import Path

import pytest

from scrapers.aetherhub import CardEntry, parse_decklist, parse_tier_list

FIXTURES = Path(__file__).parent / "fixtures"
TIER_FIXTURE = FIXTURES / "aetherhub_historic_brawl_meta.html"
BRAWL_DECK_FIXTURE = FIXTURES / "aetherhub_brawl_deck.html"
STANDARD_BO3_FIXTURE = FIXTURES / "aetherhub_standard_bo3_deck.html"


@pytest.fixture(scope="module")
def brawl_html() -> str:
    return TIER_FIXTURE.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def brawl_deck_html() -> str:
    return BRAWL_DECK_FIXTURE.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def standard_bo3_deck_html() -> str:
    return STANDARD_BO3_FIXTURE.read_text(encoding="utf-8")


# ---- Tier list ----

def test_parses_at_least_one_archetype(brawl_html):
    archetypes = parse_tier_list(brawl_html)
    assert len(archetypes) >= 1
    first = archetypes[0]
    assert first.name
    assert 0.0 <= first.meta_share <= 1.0
    assert first.decklist_url.startswith("https://aetherhub.com/")


def test_meta_shares_are_nonnegative(brawl_html):
    for arch in parse_tier_list(brawl_html):
        assert arch.meta_share >= 0.0


def test_colors_are_wubrgc_letters(brawl_html):
    allowed = {"W", "U", "B", "R", "G", "C"}
    for arch in parse_tier_list(brawl_html):
        assert all(c in allowed for c in arch.colors), f"got {arch.colors}"


def test_sample_counts_when_present_are_positive(brawl_html):
    saw_any = False
    for arch in parse_tier_list(brawl_html):
        if arch.sample_count is not None:
            assert arch.sample_count > 0
            saw_any = True
    assert saw_any, "expected at least one archetype to report a sample count"


def test_first_archetype_has_higher_share_than_last(brawl_html):
    archetypes = parse_tier_list(brawl_html)
    assert archetypes[0].meta_share >= archetypes[-1].meta_share


# ---- Decklist ----

def test_brawl_deck_parses_100_cards(brawl_deck_html):
    cards = parse_decklist(brawl_deck_html)
    total = sum(c.quantity for c in cards)
    assert total == 100, f"expected 100 cards, got {total}"


def test_brawl_deck_has_at_least_one_commander(brawl_deck_html):
    commanders = [c for c in parse_decklist(brawl_deck_html) if c.role == "commander"]
    # Partner / background decks can have 2 commanders; single-commander decks have 1.
    assert 1 <= len(commanders) <= 2, f"got {len(commanders)} commanders"


def test_brawl_deck_has_no_sideboard(brawl_deck_html):
    sideboard = [c for c in parse_decklist(brawl_deck_html) if c.role == "sideboard"]
    assert sideboard == [], f"expected no sideboard, got {sideboard}"


def test_standard_bo3_has_sideboard(standard_bo3_deck_html):
    cards = parse_decklist(standard_bo3_deck_html)
    sideboard = [c for c in cards if c.role == "sideboard"]
    mainboard = [c for c in cards if c.role == "mainboard"]
    sb_total = sum(c.quantity for c in sideboard)
    mb_total = sum(c.quantity for c in mainboard)
    assert mb_total == 60, f"expected 60-card mainboard, got {mb_total}"
    assert sb_total == 15, f"expected 15-card sideboard, got {sb_total}"


def test_standard_bo3_has_no_commander(standard_bo3_deck_html):
    commanders = [c for c in parse_decklist(standard_bo3_deck_html) if c.role == "commander"]
    assert commanders == []


def test_quantities_always_positive(brawl_deck_html, standard_bo3_deck_html):
    for html in (brawl_deck_html, standard_bo3_deck_html):
        for c in parse_decklist(html):
            assert c.quantity >= 1


def test_roles_are_valid(brawl_deck_html, standard_bo3_deck_html):
    valid = {"commander", "mainboard", "sideboard"}
    for html in (brawl_deck_html, standard_bo3_deck_html):
        for c in parse_decklist(html):
            assert c.role in valid, f"got role={c.role}"


def test_card_entry_dataclass_shape():
    entry = CardEntry(name="Sol Ring", quantity=1, role="mainboard")
    assert entry.name == "Sol Ring"
    assert entry.quantity == 1
    assert entry.role == "mainboard"
