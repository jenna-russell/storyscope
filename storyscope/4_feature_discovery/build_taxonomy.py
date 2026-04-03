#!/usr/bin/env python3
"""
Stage 4b: Build union taxonomy from multiple discovery runs.

Takes the union of features across N discovery runs to improve coverage,
then outputs a combined taxonomy ready for deduplication.

Usage:
    python -m storyscope.4_feature_discovery.build_taxonomy \
        --input-dir outputs/taxonomy \
        --output outputs/taxonomy/union_taxonomy.json
"""

from __future__ import annotations

import argparse
import json
import logging
import random
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def load_run_taxonomies(input_dir: str) -> List[Dict]:
    """Load feature_taxonomy.json from each run_N subdirectory."""
    input_path = Path(input_dir)
    taxonomies = []

    for run_dir in sorted(input_path.glob("run_*")):
        tax_file = run_dir / "feature_taxonomy.json"
        if not tax_file.exists():
            logger.warning(f"No taxonomy found in {run_dir}")
            continue
        with open(tax_file) as f:
            data = json.load(f)
        taxonomies.append(data)
        logger.info(f"Loaded taxonomy from {run_dir.name}")

    return taxonomies


def collect_all_features(taxonomies: List[Dict]) -> Dict[str, List[dict]]:
    """
    Collect all unique features across runs, keyed by feature ID.

    Returns: {feature_id: [variant_from_run1, variant_from_run2, ...]}
    """
    features_by_id: Dict[str, List[dict]] = defaultdict(list)

    for tax in taxonomies:
        for dim_key, dim_data in tax.items():
            if not isinstance(dim_data, dict):
                continue
            for aspect_key, aspect_data in dim_data.get("aspects", {}).items():
                for feat in aspect_data.get("features", []):
                    fid = feat.get("id")
                    if fid:
                        feat_with_context = {
                            **feat,
                            "_dimension": dim_key,
                            "_aspect": aspect_key,
                        }
                        features_by_id[fid].append(feat_with_context)

    return features_by_id


def build_union_taxonomy(features_by_id: Dict[str, List[dict]], seed: int = 42) -> dict:
    """
    Build a union taxonomy by selecting one variant per feature ID.

    For features that appear in multiple runs, randomly selects one run's
    version (for reproducibility).
    """
    random.seed(seed)

    # Group by dimension -> aspect -> features
    taxonomy = {}

    for fid, variants in features_by_id.items():
        # Pick one variant randomly
        chosen = random.choice(variants)
        dim_key = chosen.pop("_dimension")
        aspect_key = chosen.pop("_aspect")

        if dim_key not in taxonomy:
            taxonomy[dim_key] = {"aspects": {}}
        if aspect_key not in taxonomy[dim_key]["aspects"]:
            taxonomy[dim_key]["aspects"][aspect_key] = {"features": []}

        taxonomy[dim_key]["aspects"][aspect_key]["features"].append(chosen)

    return taxonomy


def compute_metadata(taxonomy: dict) -> dict:
    """Compute summary statistics for the taxonomy."""
    total = 0
    type_counts = defaultdict(int)
    dim_counts = {}

    for dim_key, dim_data in taxonomy.items():
        dim_total = 0
        for aspect_data in dim_data.get("aspects", {}).values():
            for feat in aspect_data.get("features", []):
                total += 1
                dim_total += 1
                type_counts[feat.get("type", "unknown")] += 1
        dim_counts[dim_key] = dim_total

    return {
        "total_features": total,
        "feature_type_counts": dict(type_counts),
        "dimension_coverage": dim_counts,
    }


def main():
    parser = argparse.ArgumentParser(description="Build union taxonomy from discovery runs")
    parser.add_argument("--input-dir", required=True, help="Directory containing run_N subdirectories")
    parser.add_argument("--output", required=True, help="Output path for union taxonomy JSON")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for variant selection")
    args = parser.parse_args()

    taxonomies = load_run_taxonomies(args.input_dir)
    if not taxonomies:
        logger.error("No taxonomies found. Run discover_features.py first.")
        return 1

    logger.info(f"Loaded {len(taxonomies)} run taxonomies")

    features_by_id = collect_all_features(taxonomies)
    logger.info(f"Found {len(features_by_id)} unique feature IDs across all runs")

    # Count how many features appear in multiple runs
    multi_run = sum(1 for v in features_by_id.values() if len(v) > 1)
    logger.info(f"Features appearing in multiple runs: {multi_run}")

    taxonomy = build_union_taxonomy(features_by_id, seed=args.seed)
    metadata = compute_metadata(taxonomy)

    output = {
        "taxonomy_metadata": metadata,
        "feature_taxonomy": taxonomy,
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")

    logger.info(f"Union taxonomy saved: {metadata['total_features']} features across "
                f"{len(taxonomy)} dimensions -> {output_path}")


if __name__ == "__main__":
    raise SystemExit(main() or 0)
