from validators.meta import validate

MINIMAL_OK = {
    "schema_version": 1,
    "generated_at": "2026-09-01T00:00:00Z",
    "sources": [],
    "formats": {
        "brawl100": {
            "archetypes": [
                {"name": "A", "meta_share": 0.15, "colors": ["U"]},
                {"name": "B", "meta_share": 0.12, "colors": ["R"]},
                {"name": "C", "meta_share": 0.10, "colors": ["G"]},
            ]
        }
    },
}


def test_valid_snapshot_passes():
    ok, warnings = validate(MINIMAL_OK)
    assert ok
    assert not warnings


def test_zero_formats_fails():
    bad = {**MINIMAL_OK, "formats": {}}
    ok, _ = validate(bad)
    assert not ok


def test_too_few_archetypes_warns_but_ok():
    thin = {
        **MINIMAL_OK,
        "formats": {
            "brawl100": {
                "archetypes": [
                    {"name": "A", "meta_share": 0.5, "colors": ["U"]},
                ]
            }
        },
    }
    ok, warnings = validate(thin)
    assert ok
    assert any("only 1 archetypes" in w for w in warnings)


def test_bad_color_letter_fails():
    bad = {
        **MINIMAL_OK,
        "formats": {
            "brawl100": {
                "archetypes": [
                    {"name": "A", "meta_share": 0.5, "colors": ["Z"]},
                ]
            }
        },
    }
    ok, _ = validate(bad)
    assert not ok


def test_negative_meta_share_fails():
    bad = {
        **MINIMAL_OK,
        "formats": {
            "brawl100": {
                "archetypes": [
                    {"name": "A", "meta_share": -0.1, "colors": ["U"]},
                ]
            }
        },
    }
    ok, _ = validate(bad)
    assert not ok


def test_empty_archetypes_allowed_no_share_warning():
    """A format with no archetypes (placeholder) should not trigger the
    meta_share range warning — the check must gate on `if fmt.archetypes`."""
    placeholder = {
        **MINIMAL_OK,
        "formats": {"brawl100": {"archetypes": []}},
    }
    ok, warnings = validate(placeholder)
    assert ok
    assert not any("total meta_share" in w for w in warnings)


def test_total_share_out_of_range_warns():
    inflated = {
        **MINIMAL_OK,
        "formats": {
            "brawl100": {
                "archetypes": [
                    {"name": "A", "meta_share": 0.99, "colors": ["U"]},
                    {"name": "B", "meta_share": 0.99, "colors": ["R"]},
                    {"name": "C", "meta_share": 0.99, "colors": ["G"]},
                ]
            }
        },
    }
    ok, warnings = validate(inflated)
    assert ok
    assert any("total meta_share" in w for w in warnings)
