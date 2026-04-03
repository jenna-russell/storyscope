#!/usr/bin/env python3
"""
Stage 5: Apply feature taxonomy to stories.

For each story, extracts values for all features in the taxonomy using
per-dimension LLM calls (10 calls per story, one per NarraBench dimension).

Usage:
    python -m storyscope.5_feature_application.apply_features \
        --csv data/stories_train.parquet \
        --taxonomy data/taxonomy.json \
        --output-dir outputs/features \
        --config config/models.yaml \
        --parallel 24
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from storyscope.providers import load_config, get_provider
from storyscope.utils.io import get_prompt_dir, safe_filename

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# Source column mapping for CSV/parquet input
SOURCE_COLUMNS = {
    "human": ["human_story"],
    "gpt": ["story_gpt", "response_gpt_5_4", "response_gpt_5.1"],
    "claude": ["story_claude", "response_claude_sonnet_4_6"],
    "deepseek": ["story_deepseek", "response_deepseek_v3_2"],
    "kimi": ["story_kimi", "response_kimi_k2_5"],
    "gemini": ["story_gemini", "response_gemini"],
}

SOURCE_ORDER = ["human", "claude", "gpt", "deepseek", "kimi", "gemini"]


# ---------------------------------------------------------------------------
# Taxonomy data classes
# ---------------------------------------------------------------------------

@dataclass
class Feature:
    id: str
    name: str
    question: str
    type: str
    values: List[str]
    condition: Optional[str] = None


@dataclass
class Dimension:
    name: str
    key: str
    description: str
    features: List[Feature] = field(default_factory=list)


@dataclass
class Taxonomy:
    dimensions: List[Dimension] = field(default_factory=list)

    @property
    def total_features(self) -> int:
        return sum(len(d.features) for d in self.dimensions)

    @classmethod
    def from_json(cls, path: str) -> "Taxonomy":
        with open(path) as f:
            data = json.load(f)
        feature_data = data.get("feature_taxonomy", data)
        taxonomy = cls()

        for dim_key, dim_data in feature_data.items():
            if dim_key in ("taxonomy_metadata", "feature_index"):
                continue
            if not isinstance(dim_data, dict):
                continue

            dim = Dimension(
                key=dim_key,
                name=dim_data.get("dimension_name", dim_key),
                description=dim_data.get("dimension_description", ""),
            )
            for aspect_data in dim_data.get("aspects", {}).values():
                for feat_data in aspect_data.get("features", []):
                    dim.features.append(Feature(
                        id=feat_data["id"],
                        name=feat_data["name"],
                        question=feat_data["question"],
                        type=feat_data["type"],
                        values=feat_data.get("values", []),
                        condition=feat_data.get("condition"),
                    ))
            if dim.features:
                taxonomy.dimensions.append(dim)

        return taxonomy


# ---------------------------------------------------------------------------
# Value normalization
# ---------------------------------------------------------------------------

def _normalize_str(s: str) -> str:
    s = str(s).strip().lower()
    s = re.sub(r'\s*\([^)]*\)', '', s)
    s = re.sub(r'[^a-z0-9]+', '_', s).strip('_')
    return s


def _best_match(raw_value: str, allowed: List[str]) -> str:
    if not allowed:
        return raw_value
    raw_norm = _normalize_str(raw_value)

    for canonical in allowed:
        if _normalize_str(canonical) == raw_norm:
            return canonical

    raw_num = re.match(r'^(\d+)', raw_norm)
    if raw_num:
        num = raw_num.group(1)
        for canonical in allowed:
            c_num = re.match(r'^(\d+)', _normalize_str(canonical))
            if c_num and c_num.group(1) == num:
                return canonical

    for canonical in allowed:
        c_norm = _normalize_str(canonical)
        if raw_norm.startswith(c_norm) or c_norm.startswith(raw_norm):
            return canonical

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
    if best_score >= 0.5 and best_canonical is not None:
        return best_canonical

    return raw_value


def normalize_features(features: Dict[str, Any], taxonomy: Taxonomy) -> Dict[str, Any]:
    """Normalize raw LLM output values to canonical taxonomy values."""
    feat_lookup = {}
    for dim in taxonomy.dimensions:
        for f in dim.features:
            feat_lookup[f.id] = (f.type, [str(v) for v in f.values])

    normalized = {}
    for fid, raw_val in features.items():
        if fid not in feat_lookup:
            continue
        ftype, allowed = feat_lookup[fid]

        if raw_val == "n/a" or raw_val is None:
            normalized[fid] = "n/a"
        elif ftype == "multi_select":
            vals = raw_val if isinstance(raw_val, list) else [raw_val]
            matched = [_best_match(str(v), allowed) for v in vals]
            seen = set()
            deduped = []
            for m in matched:
                key = _normalize_str(m)
                if key not in seen:
                    seen.add(key)
                    deduped.append(m)
            normalized[fid] = deduped
        elif ftype == "scale":
            s = str(raw_val).strip()
            num_match = re.match(r'^(\d+)', s)
            normalized[fid] = int(num_match.group(1)) if num_match else raw_val
        elif ftype in ("categorical", "ordinal", "binary"):
            normalized[fid] = _best_match(str(raw_val), allowed)
        else:
            normalized[fid] = raw_val

    return normalized


# ---------------------------------------------------------------------------
# Per-dimension prompt building
# ---------------------------------------------------------------------------

def build_dimension_prompt(dimension: Dimension, story_text: str) -> str:
    """Build a prompt for extracting features from one dimension."""
    feature_specs = []
    for f in dimension.features:
        values_str = ", ".join(str(v) for v in f.values[:10])
        if len(f.values) > 10:
            values_str += f" (+ {len(f.values) - 10} more)"
        feature_specs.append(f"**{f.id}** [{f.type}]: {f.question}")
        feature_specs.append(f"  → Values: {values_str}")
        if f.condition:
            feature_specs.append(f"  → Condition: {f.condition}")

    features_block = "\n".join(feature_specs)

    # Truncate story if necessary
    max_chars = 280000
    if len(story_text) > max_chars:
        story_text = story_text[:max_chars] + "\n\n[... story truncated ...]"

    return f"""You are a literary analyst specializing in {dimension.name.lower()}.

Extract structured features about **{dimension.name}** from the story below.
Focus area: {dimension.description}

# FEATURES TO EXTRACT

For each feature, select the appropriate value(s) from the allowed options.

**Response format rules:**
- For "binary" features: respond with exactly "yes" or "no"
- For "categorical" features: respond with exactly ONE value from the list
- For "ordinal" features: respond with exactly ONE value from the list
- For "multi_select" features: respond with a JSON array of ALL applicable values
- For "scale" features: respond with an integer within the specified range
- ONLY use values from the provided lists
- If a feature has a condition that is not met, use "n/a"
- **Never use null or omit a key** — every feature must have a value

{features_block}

# STORY TO ANALYZE

<story>
{story_text}
</story>

# OUTPUT

Return a single JSON object with feature IDs as keys.
"""


# ---------------------------------------------------------------------------
# Main extraction logic
# ---------------------------------------------------------------------------

def extract_story_features(
    provider,
    taxonomy: Taxonomy,
    story_text: str,
    dim_workers: int = 5,
) -> Tuple[Dict[str, Any], Dict]:
    """Extract all features for a single story across all dimensions."""
    all_features = {}
    dim_stats = {}

    def process_dimension(dim: Dimension):
        prompt = build_dimension_prompt(dim, story_text)
        result = provider.generate_json(prompt)
        return dim.key, result

    with ThreadPoolExecutor(max_workers=dim_workers) as executor:
        futures = {executor.submit(process_dimension, dim): dim for dim in taxonomy.dimensions}
        for future in as_completed(futures):
            dim = futures[future]
            try:
                dim_key, result = future.result()
                dim_features = {k: v for k, v in result.items() if not k.startswith("_")}
                all_features.update(dim_features)
                dim_stats[dim_key] = {"features_extracted": len(dim_features)}
            except Exception as e:
                logger.error(f"  Dimension {dim.key} failed: {e}")
                dim_stats[dim.key] = {"error": str(e)}

    normalized = normalize_features(all_features, taxonomy)
    return normalized, dim_stats


def main():
    parser = argparse.ArgumentParser(description="Apply feature taxonomy to stories")
    parser.add_argument("--csv", required=True, help="CSV or parquet with stories")
    parser.add_argument("--taxonomy", required=True, help="Path to taxonomy JSON")
    parser.add_argument("--output-dir", required=True, help="Output directory for features")
    parser.add_argument("--config", default="config/models.yaml", help="Path to models.yaml")
    parser.add_argument("--provider", default=None, help="Override provider")
    parser.add_argument("--model", default=None, help="Override model")
    parser.add_argument("--parallel", type=int, default=4, help="Number of parallel story workers")
    parser.add_argument("--dim-workers", type=int, default=5, help="Parallel dimension workers per story")
    parser.add_argument("--resume", action="store_true", help="Skip already-processed stories")
    parser.add_argument("--sources", nargs="+", default=SOURCE_ORDER, help="Sources to process")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of prompts")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be processed")
    args = parser.parse_args()

    config = load_config(args.config)
    provider = get_provider(
        config, stage="feature_application",
        provider_name=args.provider, model=args.model,
    )

    taxonomy = Taxonomy.from_json(args.taxonomy)
    logger.info(f"Taxonomy: {taxonomy.total_features} features across {len(taxonomy.dimensions)} dimensions")

    # Load stories
    if args.csv.endswith(".parquet"):
        df = pd.read_parquet(args.csv)
    else:
        df = pd.read_csv(args.csv, low_memory=False)

    if args.limit:
        df = df.head(args.limit)

    output_dir = Path(args.output_dir)

    # Build tasks
    tasks = []
    for _, row in df.iterrows():
        pid = int(row.get("prompt_id", 0))
        title = str(row.get("title", f"Story_{pid}"))

        for source in args.sources:
            story_text = None
            for col in SOURCE_COLUMNS.get(source, []):
                if col in df.columns and pd.notna(row.get(col)):
                    story_text = str(row[col])
                    break
            if not story_text:
                continue

            source_dir = output_dir / source
            safe_title = safe_filename(title)
            out_file = source_dir / f"prompt_{pid:05d}__{safe_title}.features.json"

            if args.resume and out_file.exists():
                continue

            tasks.append({
                "prompt_id": pid,
                "title": title,
                "source": source,
                "story_text": story_text,
                "out_file": out_file,
                "source_dir": source_dir,
            })

    logger.info(f"Tasks to process: {len(tasks)}")

    if args.dry_run:
        for t in tasks[:5]:
            logger.info(f"  Would process: {t['source']}/{t['title']} ({len(t['story_text'])} chars)")
        logger.info(f"  ... and {max(0, len(tasks) - 5)} more")
        return

    successful = 0
    failed = 0
    lock = threading.Lock()
    start_time = time.time()

    def worker(task):
        task["source_dir"].mkdir(parents=True, exist_ok=True)
        features, dim_stats = extract_story_features(
            provider, taxonomy, task["story_text"],
            dim_workers=args.dim_workers,
        )

        result = {
            "story_title": task["title"],
            "prompt_id": task["prompt_id"],
            "author": task["source"],
            "features": features,
            "metadata": {
                "model": provider.model,
                "total_features": taxonomy.total_features,
                "features_extracted": len(features),
                "dimension_details": dim_stats,
            },
        }
        task["out_file"].write_text(
            json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        return task["prompt_id"], task["source"]

    with ThreadPoolExecutor(max_workers=args.parallel) as executor:
        futures = {executor.submit(worker, t): t for t in tasks}
        for i, future in enumerate(as_completed(futures), 1):
            try:
                pid, source = future.result()
                with lock:
                    successful += 1
                if i % max(1, len(tasks) // 20) == 0:
                    elapsed = time.time() - start_time
                    rate = successful / elapsed if elapsed > 0 else 0
                    logger.info(f"Progress: {i}/{len(tasks)} ({successful} ok, {failed} failed, "
                                f"{rate:.1f}/s)")
            except Exception as e:
                with lock:
                    failed += 1
                task = futures[future]
                logger.error(f"Failed: {task['source']}/{task['title']}: {e}")

    elapsed = time.time() - start_time
    logger.info(f"Done: {successful} successful, {failed} failed in {elapsed:.1f}s")


if __name__ == "__main__":
    main()
