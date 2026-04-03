"""Shared I/O helpers for StoryScope pipeline."""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional


def load_prompts(path: str) -> list:
    """Load prompts JSON file. Expected format: [{id, prompt, title}, ...]"""
    with open(path) as f:
        return json.load(f)


def load_taxonomy(path: str) -> dict:
    """Load taxonomy JSON, returning the feature_taxonomy dict."""
    with open(path) as f:
        data = json.load(f)
    return data.get("feature_taxonomy", data)


def load_taxonomy_full(path: str) -> dict:
    """Load full taxonomy JSON including metadata."""
    with open(path) as f:
        return json.load(f)


def get_feature_ids(taxonomy: dict) -> List[str]:
    """Extract ordered list of feature IDs from taxonomy."""
    ids = []
    for dim_data in taxonomy.values():
        for asp_data in dim_data.get("aspects", {}).values():
            for feat in asp_data.get("features", []):
                ids.append(feat["id"])
    return ids


def get_prompt_dir() -> Path:
    """Return the path to the prompts directory."""
    return Path(__file__).parent.parent / "prompts"


def safe_filename(title: str) -> str:
    """Convert a title to a safe filename."""
    return "".join(c for c in title if c.isalnum() or c in (" ", "-", "_")).rstrip()
