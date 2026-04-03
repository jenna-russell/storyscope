#!/usr/bin/env python3
"""
Stage 3: Cross-source comparative analysis.

Compares structured narrative templates across sources (human + AI models)
to identify systematic narrative differences. Produces structured comparative
analyses that serve as input for feature discovery.

Two stages:
  Stage 1: Analyze templates from a single source to find per-source patterns
  Stage 2: Compare all source templates side-by-side for the same prompts

Usage:
    python -m storyscope.3_cross_source_comparison.compare_sources \
        --templates-dir outputs/templates \
        --output-dir outputs/comparisons \
        --config config/models.yaml --parallel 4
"""

from __future__ import annotations

import argparse
import json
import logging
import random
import time
import threading
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

# Anonymized source labels for blinding
ANON_LABELS = ["Author A", "Author B", "Author C", "Author D", "Author E", "Author F"]


def load_comparison_prompt() -> str:
    """Load the cross-source comparison prompt."""
    prompt_path = get_prompt_dir() / "cross_source_comparison.md"
    if not prompt_path.exists():
        raise FileNotFoundError(f"Comparison prompt not found: {prompt_path}")
    return prompt_path.read_text(encoding="utf-8")


def load_templates_by_prompt(templates_dir: str) -> Dict[str, Dict[str, dict]]:
    """
    Load all templates organized by prompt title.

    Returns: {title: {source: template_data, ...}, ...}
    """
    templates_dir = Path(templates_dir)
    by_prompt = defaultdict(dict)

    for source_dir in sorted(templates_dir.iterdir()):
        if not source_dir.is_dir():
            continue
        source = source_dir.name
        for tpath in sorted(source_dir.glob("*.template.json")):
            data = json.loads(tpath.read_text(encoding="utf-8"))
            title = data.get("title", tpath.stem.replace(".template", ""))
            by_prompt[title][source] = data.get("template", data)

    return dict(by_prompt)


def build_comparison_input(
    title: str,
    source_templates: Dict[str, dict],
    prompt_text: str = "",
) -> str:
    """
    Build anonymized comparison input with randomized source assignment.
    Uses deterministic randomization based on story title for reproducibility.
    """
    sources = sorted(source_templates.keys())
    random.seed(hash(title) % 2**32)
    shuffled = sources.copy()
    random.shuffle(shuffled)

    label_map = {source: ANON_LABELS[i] for i, source in enumerate(shuffled)}

    sections = []
    if prompt_text:
        sections.append(f"## Writing Prompt\n{prompt_text}\n")

    for source in shuffled:
        label = label_map[source]
        template = source_templates[source]
        template_str = json.dumps(template, indent=2, ensure_ascii=False)
        sections.append(f"## {label}'s Narrative Template\n```json\n{template_str}\n```\n")

    return "\n".join(sections), label_map


def run_comparison(
    provider,
    comparison_prompt: str,
    comparison_input: str,
) -> str:
    """Run a single comparison analysis."""
    full_prompt = f"{comparison_prompt}\n\n{comparison_input}"
    return provider.generate(full_prompt)


def main():
    parser = argparse.ArgumentParser(description="Cross-source narrative comparison")
    parser.add_argument("--templates-dir", required=True, help="Directory with source/title templates")
    parser.add_argument("--output-dir", required=True, help="Output directory for comparisons")
    parser.add_argument("--config", default="config/models.yaml", help="Path to models.yaml")
    parser.add_argument("--provider", default=None, help="Override provider")
    parser.add_argument("--model", default=None, help="Override model")
    parser.add_argument("--parallel", type=int, default=4, help="Number of parallel workers")
    parser.add_argument("--resume", action="store_true", help="Skip existing comparisons")
    parser.add_argument("--min-sources", type=int, default=2,
                        help="Minimum sources per prompt to include (default: 2)")
    parser.add_argument("--batch-size", type=int, default=3,
                        help="Number of prompts to batch per comparison call")
    args = parser.parse_args()

    config = load_config(args.config)
    provider = get_provider(
        config, stage="cross_source_comparison",
        provider_name=args.provider, model=args.model,
    )

    comparison_prompt = load_comparison_prompt()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load templates
    by_prompt = load_templates_by_prompt(args.templates_dir)
    logger.info(f"Loaded templates for {len(by_prompt)} prompts")

    # Filter to prompts with enough sources
    eligible = {title: sources for title, sources in by_prompt.items()
                if len(sources) >= args.min_sources}
    logger.info(f"Eligible prompts (>= {args.min_sources} sources): {len(eligible)}")

    # Build batched tasks
    titles = sorted(eligible.keys())
    batches = []
    for i in range(0, len(titles), args.batch_size):
        batch_titles = titles[i : i + args.batch_size]
        batches.append(batch_titles)

    # Filter for resume
    tasks = []
    skipped = 0
    for batch_idx, batch_titles in enumerate(batches):
        out_file = output_dir / f"stage2_batch_{batch_idx:04d}_analysis.json"
        if args.resume and out_file.exists():
            skipped += 1
            continue
        tasks.append((batch_idx, batch_titles, out_file))

    logger.info(f"Batches to process: {len(tasks)} (skipped {skipped})")

    successful = 0
    failed = 0
    lock = threading.Lock()

    def worker(task_tuple):
        batch_idx, batch_titles, out_file = task_tuple

        batch_inputs = []
        batch_label_maps = {}
        for title in batch_titles:
            comparison_input, label_map = build_comparison_input(
                title, eligible[title]
            )
            batch_inputs.append(f"# Story: {title}\n\n{comparison_input}")
            batch_label_maps[title] = label_map

        combined_input = "\n\n---\n\n".join(batch_inputs)
        analysis = run_comparison(provider, comparison_prompt, combined_input)

        result = {
            "batch_idx": batch_idx,
            "titles": batch_titles,
            "label_maps": batch_label_maps,
            "analysis": analysis,
        }
        out_file.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        return batch_idx

    with ThreadPoolExecutor(max_workers=args.parallel) as executor:
        futures = {executor.submit(worker, t): t for t in tasks}
        for i, future in enumerate(as_completed(futures), 1):
            try:
                future.result()
                with lock:
                    successful += 1
                if i % max(1, len(tasks) // 10) == 0:
                    logger.info(f"Progress: {i}/{len(tasks)} ({successful} ok, {failed} failed)")
            except Exception as e:
                with lock:
                    failed += 1
                logger.error(f"Batch failed: {e}")

    logger.info(f"Done: {successful} successful, {failed} failed")


if __name__ == "__main__":
    main()
