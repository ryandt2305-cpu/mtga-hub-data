"""Meta snapshot validator.

Mirrors the Rust MetaSnapshot schema (mtga-tool:
src-tauri/src/models/meta_snapshot.rs). Uses pydantic to enforce types
and adds sanity thresholds beyond bare-shape validation.
"""
from __future__ import annotations

import json

from pydantic import BaseModel, Field, field_validator


class MetaCardEntryModel(BaseModel):
    name: str
    quantity: int = Field(ge=1)
    role: str = "mainboard"


class MetaArchetypeModel(BaseModel):
    name: str
    meta_share: float = Field(ge=0.0, le=1.0)
    sample_count: int | None = None
    colors: list[str] = Field(default_factory=list)
    representative_decklist_url: str = ""
    decklist: list[MetaCardEntryModel] = Field(default_factory=list)

    @field_validator("colors")
    @classmethod
    def _colors_wubrg(cls, v: list[str]) -> list[str]:
        allowed = {"W", "U", "B", "R", "G", "C"}
        for c in v:
            if c not in allowed:
                raise ValueError(f"invalid color letter: {c}")
        return v


class MetaFormatModel(BaseModel):
    aetherhub_format_key: str | None = None
    single_source: bool = True
    sample_size: int | None = None
    sample_window_days: int | None = None
    archetypes: list[MetaArchetypeModel] = Field(default_factory=list)


class MetaSourceModel(BaseModel):
    name: str
    url: str
    fetched_at: str


class MetaSnapshotModel(BaseModel):
    schema_version: int = Field(ge=1)
    generated_at: str
    sources: list[MetaSourceModel] = Field(default_factory=list)
    formats: dict[str, MetaFormatModel] = Field(default_factory=dict)


MIN_ARCHETYPES_PER_ACTIVE_FORMAT = 3
MAX_ALLOWED_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


def validate(snapshot_dict: dict) -> tuple[bool, list[str]]:
    warnings: list[str] = []
    try:
        snap = MetaSnapshotModel.model_validate(snapshot_dict)
    except Exception as e:
        return False, [f"schema: {e}"]

    if not snap.formats:
        return False, ["snapshot has zero formats"]

    for name, fmt in snap.formats.items():
        # "active" = has archetypes. Empty formats are allowed as placeholders.
        if fmt.archetypes and len(fmt.archetypes) < MIN_ARCHETYPES_PER_ACTIVE_FORMAT:
            warnings.append(
                f"{name}: only {len(fmt.archetypes)} archetypes "
                f"(threshold {MIN_ARCHETYPES_PER_ACTIVE_FORMAT})"
            )
        # meta_share values should sum to something plausible (0.30–1.50 range —
        # not exactly 1.0 because Aetherhub aggregates a long tail into "other").
        total_share = sum(a.meta_share for a in fmt.archetypes)
        if fmt.archetypes and (total_share < 0.30 or total_share > 1.50):
            warnings.append(
                f"{name}: total meta_share {total_share:.2f} outside [0.30, 1.50]"
            )

    size = len(json.dumps(snapshot_dict).encode("utf-8"))
    if size > MAX_ALLOWED_SIZE_BYTES:
        return False, [f"snapshot size {size} > {MAX_ALLOWED_SIZE_BYTES}"]

    return True, warnings
