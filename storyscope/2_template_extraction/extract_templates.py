#!/usr/bin/env python3
"""
Stage 2: Extract structured narrative templates from stories.

Transforms each story into a NarraBench-based structured representation
that preserves narrative elements while abstracting away surface wording.

Usage:
    # From a directory of story files
    python -m storyscope.2_template_extraction.extract_templates \
        --stories-dir outputs/stories \
        --output-dir outputs/templates \
        --config config/models.yaml --parallel 4

    # From a CSV dataset
    python -m storyscope.2_template_extraction.extract_templates \
        --csv data/stories_train.parquet \
        --output-dir outputs/templates \
        --config config/models.yaml --parallel 4
"""

from __future__ import annotations

import argparse
import json
import logging
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Dict

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
    "claude": ["story_claude", "response_claude_sonnet_4_6", "response_claude_opus_4_5_20251101"],
    "deepseek": ["story_deepseek", "response_deepseek_v3_2", "response_deepseek_ai_DeepSeek_V3"],
    "kimi": ["story_kimi", "response_kimi_k2_5", "response_moonshotai_Kimi_K2_Instruct"],
    "gemini": ["story_gemini", "response_gemini"],
}


def load_template_prompt() -> str:
    """Load the NarraBench template extraction prompt."""
    prompt_path = get_prompt_dir() / "template_extraction.md"
    if not prompt_path.exists():
        raise FileNotFoundError(f"Template extraction prompt not found: {prompt_path}")
    return prompt_path.read_text(encoding="utf-8")


def extract_template(provider, story_text: str, template_prompt: str) -> dict:
    """Extract a structured template from a story."""
    full_prompt = template_prompt.replace("{narrative_text}", story_text)
    return provider.generate_json(full_prompt)


def collect_tasks_from_csv(csv_path: str, sources: List[str]) -> List[Dict]:
    """Build extraction tasks from a CSV/parquet file."""
    if csv_path.endswith(".parquet"):
        df = pd.read_parquet(csv_path)
    else:
        df = pd.read_csv(csv_path, low_memory=False)

    tasks = []
    for _, row in df.iterrows():
        pid = int(row.get("prompt_id", 0))
        title = row.get("title", f"Story_{pid}")

        for source in sources:
            story_text = None
            for col in SOURCE_COLUMNS.get(source, []):
                if col in df.columns and pd.notna(row.get(col)):
                    story_text = str(row[col])
                    break
            if story_text:
                tasks.append({
                    "prompt_id": pid,
                    "title": title,
                    "source": source,
                    "story_text": story_text,
                })
    return tasks


def collect_tasks_from_dir(stories_dir: str) -> List[Dict]:
    """Build extraction tasks from a directory of story files."""
    tasks = []
    stories_path = Path(stories_dir)
    for story_dir in sorted(stories_path.iterdir()):
        if not story_dir.is_dir():
            continue
        story_file = story_dir / "story.txt"
        meta_file = story_dir / "metadata.json"
        if not story_file.exists():
            continue

        story_text = story_file.read_text(encoding="utf-8")
        meta = {}
        if meta_file.exists():
            meta = json.loads(meta_file.read_text(encoding="utf-8"))

        tasks.append({
            "prompt_id": meta.get("prompt_id", story_dir.name.split("_")[0]),
            "title": meta.get("title", story_dir.name),
            "source": "generated",
            "story_text": story_text,
        })
    return tasks


def main():
    parser = argparse.ArgumentParser(description="Extract structured narrative templates")
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--stories-dir", help="Directory containing story subdirectories")
    input_group.add_argument("--csv", help="CSV or parquet file with stories")
    parser.add_argument("--output-dir", required=True, help="Output directory for templates")
    parser.add_argument("--config", default="config/models.yaml", help="Path to models.yaml")
    parser.add_argument("--provider", default=None, help="Override provider")
    parser.add_argument("--model", default=None, help="Override model")
    parser.add_argument("--parallel", type=int, default=4, help="Number of parallel workers")
    parser.add_argument("--resume", action="store_true", help="Skip existing templates")
    parser.add_argument("--sources", nargs="+", default=list(SOURCE_COLUMNS.keys()),
                        help="Sources to extract (default: all)")
    args = parser.parse_args()

    config = load_config(args.config)
    provider = get_provider(
        config, stage="template_extraction",
        provider_name=args.provider, model=args.model,
    )

    template_prompt = load_template_prompt()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Collect tasks
    if args.csv:
        tasks = collect_tasks_from_csv(args.csv, args.sources)
    else:
        tasks = collect_tasks_from_dir(args.stories_dir)

    # Filter for resume
    if args.resume:
        filtered = []
        for t in tasks:
            out_file = output_dir / t["source"] / f"{safe_filename(t['title'])}.template.json"
            if not out_file.exists():
                filtered.append(t)
        skipped = len(tasks) - len(filtered)
        tasks = filtered
        logger.info(f"Resuming: skipped {skipped} existing templates")

    logger.info(f"Extracting {len(tasks)} templates using {provider.model}")

    successful = 0
    failed = 0
    lock = threading.Lock()
    start_time = time.time()

    def worker(task):
        source_dir = output_dir / task["source"]
        source_dir.mkdir(parents=True, exist_ok=True)
        out_file = source_dir / f"{safe_filename(task['title'])}.template.json"

        template = extract_template(provider, task["story_text"], template_prompt)
        result = {
            "prompt_id": task["prompt_id"],
            "title": task["title"],
            "source": task["source"],
            "template": template,
        }
        out_file.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        return task["title"]

    with ThreadPoolExecutor(max_workers=args.parallel) as executor:
        futures = {executor.submit(worker, t): t for t in tasks}
        for i, future in enumerate(as_completed(futures), 1):
            try:
                future.result()
                with lock:
                    successful += 1
                if i % max(1, len(tasks) // 20) == 0:
                    logger.info(f"Progress: {i}/{len(tasks)} ({successful} ok, {failed} failed)")
            except Exception as e:
                with lock:
                    failed += 1
                logger.error(f"Failed: {futures[future]['title']}: {e}")

    elapsed = time.time() - start_time
    logger.info(f"Done: {successful} successful, {failed} failed in {elapsed:.1f}s")


if __name__ == "__main__":
    main()
