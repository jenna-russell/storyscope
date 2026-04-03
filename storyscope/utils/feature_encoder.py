"""
Feature encoding module for StoryScope classification experiments.

Provides taxonomy loading, feature matrix construction, and encoding
strategies for training classifiers on narrative features.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder


def load_taxonomy(path: str) -> dict:
    """Load taxonomy JSON file, returning the feature_taxonomy dict."""
    with open(path) as f:
        data = json.load(f)
    return data.get("feature_taxonomy", data)


def build_feature_type_map(taxonomy: dict) -> Dict[str, dict]:
    """
    Build a map: {feature_id: {type, name, values, dimension}}
    """
    fmap = {}
    for dim_key, dim_data in taxonomy.items():
        dim_name = dim_data.get("dimension_name", dim_key)
        for asp_key, asp_data in dim_data.get("aspects", {}).items():
            for feat in asp_data.get("features", []):
                fmap[feat["id"]] = {
                    "type": feat.get("type", "categorical"),
                    "name": feat.get("name", feat["id"]),
                    "values": feat.get("values", []),
                    "dimension": dim_name,
                }
    return fmap


def get_taxonomy_feature_ids(taxonomy: dict) -> List[str]:
    """Extract ordered list of feature IDs from taxonomy."""
    ids = []
    for dim_data in taxonomy.values():
        for asp_data in dim_data.get("aspects", {}).values():
            for feat in asp_data.get("features", []):
                ids.append(feat["id"])
    return ids


def _normalize_str(s: str) -> str:
    """Reduce a value string to a canonical comparable form."""
    s = str(s).strip().lower()
    s = re.sub(r'\s*\([^)]*\)', '', s)
    s = re.sub(r'[^a-z0-9]+', '_', s).strip('_')
    return s


def _best_match(raw_value: str, allowed: List[str]) -> str:
    """Fuzzy-match a raw value to the closest taxonomy value."""
    if not allowed:
        return raw_value

    raw_norm = _normalize_str(raw_value)

    # 1) Exact match on normalized form
    for canonical in allowed:
        if _normalize_str(canonical) == raw_norm:
            return canonical

    # 2) Numeric prefix match
    raw_num = re.match(r'^(\d+)', raw_norm)
    if raw_num:
        num = raw_num.group(1)
        for canonical in allowed:
            c_num = re.match(r'^(\d+)', _normalize_str(canonical))
            if c_num and c_num.group(1) == num:
                return canonical

    # 3) Prefix/substring match
    for canonical in allowed:
        c_norm = _normalize_str(canonical)
        if raw_norm.startswith(c_norm) or c_norm.startswith(raw_norm):
            return canonical

    # 4) Token overlap
    raw_tokens = set(raw_norm.split('_'))
    best_score, best_canonical = 0, None
    for canonical in allowed:
        c_tokens = set(_normalize_str(canonical).split('_'))
        if not c_tokens:
            continue
        overlap = len(raw_tokens & c_tokens)
        score = overlap / max(len(raw_tokens), len(c_tokens))
        if score > best_score:
            best_score, best_canonical = score, canonical
    if best_score >= 0.33 and best_canonical is not None:
        return best_canonical

    return raw_value


def load_features_matrix(
    features_dir: str,
    taxonomy: dict,
    normalize: bool = True,
) -> Tuple[pd.DataFrame, List[str], List[str]]:
    """
    Load feature JSONs from author subdirectories into a DataFrame.

    Returns:
        df: DataFrame with columns [author, story_title, prompt_id, <feature_id>...]
        feature_ids: ordered list of taxonomy feature IDs
        authors: sorted list of author names found
    """
    feature_ids = get_taxonomy_feature_ids(taxonomy)
    features_dir = Path(features_dir)
    rows = []
    authors_found = set()

    for author_dir in sorted(features_dir.iterdir()):
        if not author_dir.is_dir():
            continue
        author = author_dir.name
        authors_found.add(author)

        for fpath in sorted(author_dir.glob("*.features.json")):
            with open(fpath) as f:
                data = json.load(f)
            story_title = data.get("story_title", fpath.stem.replace(".features", ""))
            features = data.get("features", {})

            row = {
                "author": author,
                "story_title": story_title,
                "prompt_id": data.get("prompt_id"),
            }
            for fid in feature_ids:
                row[fid] = features.get(fid, None)
            rows.append(row)

    df = pd.DataFrame(rows)
    authors = sorted(authors_found)
    return df, feature_ids, authors


def load_features_parquet(
    parquet_path: str,
    taxonomy: dict,
) -> Tuple[pd.DataFrame, List[str], List[str]]:
    """
    Load features from a parquet file (as produced by data preparation).

    Returns:
        df: DataFrame with columns [author, story_title, prompt_id, <feature_id>...]
        feature_ids: ordered list of taxonomy feature IDs
        authors: sorted list of source names found
    """
    df = pd.read_parquet(parquet_path)
    feature_ids = get_taxonomy_feature_ids(taxonomy)

    # Rename 'source' to 'author' for compatibility
    if "source" in df.columns and "author" not in df.columns:
        df = df.rename(columns={"source": "author"})

    authors = sorted(df["author"].unique())
    return df, feature_ids, authors


def encode_features(
    df: pd.DataFrame,
    feature_ids: List[str],
    feature_type_map: Dict[str, dict],
    mode: str = "first_value",
) -> Tuple[np.ndarray, List[str]]:
    """
    Encode feature columns into a numeric matrix.

    Args:
        mode: one of "first_value", "multi_hot", "multi_hot_count"

    Returns:
        X: numpy array (n_samples, n_encoded_cols)
        col_names: list of column names for X
    """
    encoded_cols = []
    col_names = []

    for fid in feature_ids:
        finfo = feature_type_map.get(fid, {})
        ftype = finfo.get("type", "categorical")
        taxonomy_values = finfo.get("values", [])

        col = df[fid].copy()

        if ftype == "multi_select" and mode in ("multi_hot", "multi_hot_count"):
            for val in taxonomy_values:
                binary_col = col.apply(
                    lambda x, v=val: (
                        1 if isinstance(x, list) and v in x
                        else 1 if isinstance(x, str) and v in x.split("|")
                        else 0
                    )
                )
                encoded_cols.append(binary_col.values)
                col_names.append(f"{fid}__{val}")

            if mode == "multi_hot_count":
                count_col = col.apply(
                    lambda x: len(x) if isinstance(x, list)
                    else len(x.split("|")) if isinstance(x, str) and x
                    else 0
                )
                encoded_cols.append(count_col.values)
                col_names.append(f"{fid}__count")
        else:
            def _to_str(x):
                if isinstance(x, list):
                    return str(x[0]) if x else "__MISSING__"
                if x is None or (isinstance(x, float) and np.isnan(x)):
                    return "__MISSING__"
                return str(x)

            str_col = col.apply(_to_str)
            le = LabelEncoder()
            le.fit(sorted(str_col.unique()))
            encoded_cols.append(le.transform(str_col))
            col_names.append(fid)

    X = np.column_stack(encoded_cols)
    return X, col_names


def filter_matched_prompts(df: pd.DataFrame, authors: List[str]) -> pd.DataFrame:
    """Keep only story_titles present for all authors."""
    n_authors = len(authors)
    counts = df.groupby("story_title")["author"].nunique()
    matched = counts[counts == n_authors].index
    return df[df["story_title"].isin(matched)].copy()


def build_groups(df: pd.DataFrame) -> np.ndarray:
    """Map story_title to integer group IDs for GroupKFold."""
    titles = df["story_title"].values
    unique_titles = sorted(set(titles))
    title_to_id = {t: i for i, t in enumerate(unique_titles)}
    return np.array([title_to_id[t] for t in titles])


def make_binary_target(df: pd.DataFrame) -> np.ndarray:
    """Human=1, all AI=0."""
    return (df["author"] == "human").astype(int).values


def make_multiclass_target(
    df: pd.DataFrame, authors: List[str]
) -> Tuple[np.ndarray, Dict[str, int]]:
    """Map authors to integer class indices."""
    label_map = {a: i for i, a in enumerate(authors)}
    y = df["author"].map(label_map).values
    return y, label_map


def friendly_col_name(col: str, feature_type_map: Dict[str, dict]) -> str:
    """Convert encoded column name to human-readable form."""
    if "__" in col:
        fid, val = col.rsplit("__", 1)
        finfo = feature_type_map.get(fid, {})
        fname = finfo.get("name", fid)
        if val == "count":
            return f"{fname} (count)"
        return f"{fname}: {val}"
    else:
        finfo = feature_type_map.get(col, {})
        return finfo.get("name", col)
