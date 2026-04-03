#!/usr/bin/env python3
"""
Stage 1: Generate AI stories from writing prompts.

Given a JSON file of prompts (each with id, title, prompt), generates stories
using a configurable LLM provider and saves them in a structured layout.

Usage:
    python -m storyscope.1_story_generation.generate_stories \
        --prompts prompts.json \
        --output-dir outputs/stories \
        --config config/models.yaml \
        --parallel 4
"""

from __future__ import annotations

import argparse
import json
import logging
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from storyscope.providers import load_config, get_provider
from storyscope.utils.io import load_prompts, safe_filename

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

SYSTEM_PROMPT = "You are a creative writing expert who generates rich, detailed stories."


def generate_story(provider, prompt_text: str) -> str:
    """Generate a single story using the configured provider."""
    return provider.generate(prompt_text, system=SYSTEM_PROMPT)


def main():
    parser = argparse.ArgumentParser(description="Generate AI stories from prompts")
    parser.add_argument("--prompts", required=True, help="Path to prompts JSON file")
    parser.add_argument("--output-dir", required=True, help="Output directory for stories")
    parser.add_argument("--config", default="config/models.yaml", help="Path to models.yaml")
    parser.add_argument("--provider", default=None, help="Override provider (openai, anthropic, vertex, huggingface)")
    parser.add_argument("--model", default=None, help="Override model name")
    parser.add_argument("--parallel", type=int, default=1, help="Number of parallel workers")
    parser.add_argument("--resume", action="store_true", help="Skip already-generated stories")
    parser.add_argument("--max-stories", type=int, default=None, help="Limit number of stories")
    parser.add_argument("--start-from", type=int, default=1, help="Start from prompt ID")
    args = parser.parse_args()

    config = load_config(args.config)
    provider = get_provider(
        config, stage="story_generation",
        provider_name=args.provider, model=args.model,
    )

    prompts_data = load_prompts(args.prompts)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Filter and prepare tasks
    tasks = []
    skipped = 0
    for p in prompts_data:
        pid = int(p.get("id", 0))
        if pid < args.start_from:
            continue
        title = p.get("title", f"Story_{pid}")
        prompt_text = p.get("prompt", "")
        if not prompt_text:
            continue

        safe_title = safe_filename(title)
        story_dir = output_dir / f"{pid}_{safe_title}"
        story_file = story_dir / "story.txt"

        if args.resume and story_file.exists():
            skipped += 1
            continue

        tasks.append({"id": pid, "title": title, "prompt": prompt_text, "file": story_file, "dir": story_dir})
        if args.max_stories and len(tasks) >= args.max_stories:
            break

    logger.info(f"Queued: {len(tasks)}, Skipped: {skipped}")

    successful = 0
    failed = 0
    lock = threading.Lock()
    start_time = time.time()

    def worker(task):
        task["dir"].mkdir(parents=True, exist_ok=True)
        story = generate_story(provider, task["prompt"])
        task["file"].write_text(story, encoding="utf-8")

        # Save metadata
        meta = {
            "prompt_id": task["id"],
            "title": task["title"],
            "prompt": task["prompt"],
            "model": provider.model,
            "story_length_chars": len(story),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        meta_file = task["dir"] / "metadata.json"
        meta_file.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
        return task["id"]

    with ThreadPoolExecutor(max_workers=args.parallel) as executor:
        futures = {executor.submit(worker, t): t for t in tasks}
        for i, future in enumerate(as_completed(futures), 1):
            try:
                pid = future.result()
                with lock:
                    successful += 1
                if i % max(1, len(tasks) // 20) == 0:
                    elapsed = time.time() - start_time
                    logger.info(f"Progress: {i}/{len(tasks)} ({successful} ok, {failed} failed) [{elapsed:.0f}s]")
            except Exception as e:
                with lock:
                    failed += 1
                logger.error(f"Failed: {futures[future]['title']}: {e}")

    elapsed = time.time() - start_time
    logger.info(f"Done: {successful} successful, {failed} failed in {elapsed:.1f}s")


if __name__ == "__main__":
    main()
