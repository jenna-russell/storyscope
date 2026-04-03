#!/usr/bin/env bash
# StoryScope Pipeline - Example end-to-end run
#
# This script demonstrates running the full pipeline on the dev set (100 prompts).
# Adjust --parallel and provider settings in config/models.yaml for your setup.
#
# Prerequisites:
#   pip install -r requirements.txt
#   export OPENAI_API_KEY="sk-..."  (or configure your preferred provider)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$SCRIPT_DIR"

CONFIG="config/models.yaml"
OUTPUT="outputs"

echo "=== StoryScope Pipeline ==="
echo "Working directory: $SCRIPT_DIR"
echo ""

# Stage 1: Generate stories (skip if using pre-generated data)
echo "--- Stage 1: Story Generation ---"
python -m storyscope.1_story_generation.generate_stories \
    --prompts data/prompts.json \
    --output-dir "$OUTPUT/stories" \
    --config "$CONFIG" \
    --parallel 4 \
    --resume

# Stage 2: Extract templates
echo ""
echo "--- Stage 2: Template Extraction ---"
python -m storyscope.2_template_extraction.extract_templates \
    --csv data/stories_dev.parquet \
    --output-dir "$OUTPUT/templates" \
    --config "$CONFIG" \
    --parallel 4 \
    --resume

# Stage 3: Cross-source comparison
echo ""
echo "--- Stage 3: Cross-Source Comparison ---"
python -m storyscope.3_cross_source_comparison.compare_sources \
    --templates-dir "$OUTPUT/templates" \
    --output-dir "$OUTPUT/comparisons" \
    --config "$CONFIG" \
    --parallel 4 \
    --resume

# Stage 4: Feature discovery + deduplication
echo ""
echo "--- Stage 4a: Feature Discovery (3 runs) ---"
python -m storyscope.4_feature_discovery.discover_features \
    --comparisons-dir "$OUTPUT/comparisons" \
    --output-dir "$OUTPUT/taxonomy" \
    --config "$CONFIG" \
    --runs 3

echo ""
echo "--- Stage 4b: Build Union Taxonomy ---"
python -m storyscope.4_feature_discovery.build_taxonomy \
    --input-dir "$OUTPUT/taxonomy" \
    --output "$OUTPUT/taxonomy/union_taxonomy.json"

echo ""
echo "--- Stage 4c: Deduplicate Features ---"
python -m storyscope.4_feature_discovery.cluster_features \
    --taxonomy "$OUTPUT/taxonomy/union_taxonomy.json" \
    --output-dir "$OUTPUT/taxonomy/clustered" \
    --sim-threshold 0.85

# Stage 5: Apply features
echo ""
echo "--- Stage 5: Feature Application ---"
python -m storyscope.5_feature_application.apply_features \
    --csv data/stories_dev.parquet \
    --taxonomy data/taxonomy.json \
    --output-dir "$OUTPUT/features" \
    --config "$CONFIG" \
    --parallel 4

# Stage 6: Classification & SHAP
echo ""
echo "--- Stage 6a: Train Classifiers ---"
python -m storyscope.6_classification.train_classifier \
    --features data/storyscope_features.parquet \
    --taxonomy data/taxonomy.json \
    --output-dir "$OUTPUT/classification" \
    --task both

echo ""
echo "--- Stage 6b: SHAP Analysis ---"
python -m storyscope.6_classification.shap_analysis \
    --features data/storyscope_features.parquet \
    --taxonomy data/taxonomy.json \
    --output-dir "$OUTPUT/shap" \
    --task both \
    --bootstrap 50

echo ""
echo "=== Pipeline Complete ==="
