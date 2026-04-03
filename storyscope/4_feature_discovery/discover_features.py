#!/usr/bin/env python3
"""
Stage 4a: Discover narrative features from cross-source comparisons.

Runs one LLM call per NarraBench dimension, each focused on extracting
discriminative features for that dimension. The 10 dimension results are
then merged into a unified feature taxonomy.

Usage:
    python -m storyscope.4_feature_discovery.discover_features \
        --comparisons-dir outputs/comparisons \
        --output-dir outputs/taxonomy \
        --config config/models.yaml \
        --runs 3
"""

from __future__ import annotations

import argparse
import json
import logging
import time
import re
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List

from storyscope.providers import load_config, get_provider
from storyscope.utils.io import get_prompt_dir

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# Per-dimension prompt files
DIMENSION_PROMPTS = {
    "agents": "aspect_agents.md",
    "social_networks": "aspect_social_networks.md",
    "events": "aspect_events.md",
    "plot": "aspect_plot.md",
    "setting": "aspect_setting.md",
    "temporal_structure": "aspect_temporal_structure.md",
    "revelation": "aspect_revelation.md",
    "perspective": "aspect_perspective.md",
    "style": "aspect_style.md",
    "situatedness": "aspect_situatedness.md",
}


def load_comparison_data(comparisons_dir: str) -> List[Dict]:
    """Load stage 2 comparison batch files."""
    batches = []
    cdir = Path(comparisons_dir)
    for f in sorted(cdir.glob("stage2_batch_*_analysis.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            batches.append(data)
        except Exception as e:
            logger.warning(f"Could not load {f.name}: {e}")
    return batches


def format_observations(batches: List[Dict], dimension: str) -> str:
    """Extract and format observations relevant to a specific dimension."""
    sections = []
    for i, batch in enumerate(batches, 1):
        analysis = batch.get("analysis", "")
        if analysis:
            sections.append(f"**Batch {i} analysis:**\n{analysis}")
    return "\n\n".join(sections)


def discover_dimension_features(
    provider,
    dimension: str,
    observations: str,
) -> dict:
    """Run feature discovery for a single dimension."""
    prompt_dir = get_prompt_dir()
    prompt_file = prompt_dir / DIMENSION_PROMPTS[dimension]

    if not prompt_file.exists():
        raise FileNotFoundError(f"Aspect prompt not found: {prompt_file}")

    expert_prompt = prompt_file.read_text(encoding="utf-8")
    full_prompt = f"{expert_prompt}\n\n# OBSERVATIONS\n\n{observations}"

    return provider.generate_json(full_prompt)


def main():
    parser = argparse.ArgumentParser(description="Discover narrative features per dimension")
    parser.add_argument("--comparisons-dir", required=True, help="Directory with comparison analyses")
    parser.add_argument("--output-dir", required=True, help="Output directory for taxonomy")
    parser.add_argument("--config", default="config/models.yaml", help="Path to models.yaml")
    parser.add_argument("--provider", default=None, help="Override provider")
    parser.add_argument("--model", default=None, help="Override model")
    parser.add_argument("--runs", type=int, default=3, help="Number of discovery runs for stability")
    parser.add_argument("--dimensions", nargs="+", default=list(DIMENSION_PROMPTS.keys()),
                        help="Dimensions to discover (default: all 10)")
    args = parser.parse_args()

    config = load_config(args.config)
    provider = get_provider(
        config, stage="feature_discovery",
        provider_name=args.provider, model=args.model,
    )

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load comparison data
    batches = load_comparison_data(args.comparisons_dir)
    logger.info(f"Loaded {len(batches)} comparison batches")

    for run_idx in range(1, args.runs + 1):
        logger.info(f"=== Discovery Run {run_idx}/{args.runs} ===")
        run_dir = output_dir / f"run_{run_idx}"
        run_dir.mkdir(parents=True, exist_ok=True)

        taxonomy = {}
        for dim in args.dimensions:
            logger.info(f"  Discovering features for: {dim}")
            observations = format_observations(batches, dim)

            try:
                result = discover_dimension_features(provider, dim, observations)
                taxonomy[dim] = result
                # Save per-dimension result
                dim_file = run_dir / f"{dim}_features.json"
                dim_file.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
                n_features = len(result.get("features", result.get("aspects", {}).keys()))
                logger.info(f"    {dim}: extracted features")
            except Exception as e:
                logger.error(f"    {dim}: FAILED - {e}")
                taxonomy[dim] = {"error": str(e)}

        # Save combined taxonomy for this run
        run_file = run_dir / "feature_taxonomy.json"
        run_file.write_text(json.dumps(taxonomy, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info(f"  Run {run_idx} saved to {run_file}")

    logger.info("Feature discovery complete. Run build_taxonomy.py to merge runs.")


if __name__ == "__main__":
    main()
