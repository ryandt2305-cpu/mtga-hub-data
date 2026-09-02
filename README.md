# mtga-hub-data

Aggregator for MTGA Hub's external-data lane. Runs a daily GitHub Actions
scrape of publicly available MTGA meta data, normalizes it to a versioned
JSON schema, publishes it via GitHub Pages.

## Data sources

- **Aetherhub** — constructed-format tier lists + representative
  decklists per archetype. Coverage: Standard, Alchemy, Historic,
  Explorer, Timeless, Brawl (60-card), Historic Brawl (100-card).

## Published URLs

- `https://ryandt2305-cpu.github.io/mtga-hub-data/data/meta.json`

## Attribution

All data is derived from public tracker pages on the source sites.
This repository publishes only aggregated / derived data with links
back to the source. No editorial content or original site markup is
reproduced.

## Takedown

If you represent a source site and want your data removed, please open
an issue on this repository. We'll remove the relevant scraper and
republish `data/meta.json` with the affected fields empty, typically
within 24 hours.

## Schema

See the MTGA Hub design spec for the `meta.json` shape:
`docs/superpowers/specs/2026-09-01-external-data-architecture-design.md`
in the mtga-tool repo.

## Development

```
python -m venv .venv && source .venv/bin/activate  # or .venv/Scripts/activate on Windows
pip install -r requirements.txt
python -m scripts.build_meta   # runs the full pipeline locally
pytest                          # tests
ruff check .                    # lint
```

GitHub Actions runs the same commands on a daily cron (06:00 UTC) and
on manual dispatch.
