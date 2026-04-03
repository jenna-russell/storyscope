#!/usr/bin/env python3
"""
Stage 4c: Deduplicate features via embedding-based clustering.

Encodes each feature's text description with a language model, clusters by
cosine similarity, and retains the feature nearest each cluster centroid.
This reduces the raw union taxonomy (e.g., 408 features) to a deduplicated
set (e.g., 304 features).

Usage:
    # Embedding-based deduplication (requires GPU + transformers)
    python -m storyscope.4_feature_discovery.cluster_features \
        --taxonomy outputs/taxonomy/union_taxonomy.json \
        --output-dir outputs/taxonomy/clustered \
        --method embedding \
        --sim-threshold 0.85

    # Pearson correlation-based (CPU only, requires feature matrix)
    python -m storyscope.4_feature_discovery.cluster_features \
        --taxonomy outputs/taxonomy/union_taxonomy.json \
        --features-dir outputs/features_by_author \
        --output-dir outputs/taxonomy/clustered \
        --method pearson \
        --sim-threshold 0.85
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def load_taxonomy_features(taxonomy_path: str) -> Tuple[dict, List[dict]]:
    """Load taxonomy and return (full_data, flat list of features with context)."""
    with open(taxonomy_path) as f:
        data = json.load(f)

    taxonomy = data.get("feature_taxonomy", data)
    features = []

    for dim_key, dim_data in taxonomy.items():
        if not isinstance(dim_data, dict):
            continue
        for asp_key, asp_data in dim_data.get("aspects", {}).items():
            for feat in asp_data.get("features", []):
                features.append({
                    **feat,
                    "_dimension": dim_key,
                    "_aspect": asp_key,
                })

    return data, features


def feature_to_text(feat: dict) -> str:
    """Convert a feature to a text representation for embedding."""
    name = feat.get("name", feat.get("id", ""))
    question = feat.get("question", "")
    values = ", ".join(str(v) for v in feat.get("values", []))
    return f"{name}: {question}  Values: {values}"


def compute_embeddings(features: List[dict], model_name: str, batch_size: int = 8, device: str = "auto") -> np.ndarray:
    """Compute embeddings for all features using a HuggingFace model."""
    import torch
    from transformers import AutoTokenizer, AutoModel

    if device == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"

    logger.info(f"Loading embedding model: {model_name} on {device}")
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    model = AutoModel.from_pretrained(model_name, trust_remote_code=True).to(device)
    model.eval()

    texts = [feature_to_text(f) for f in features]
    all_embeddings = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        inputs = tokenizer(batch, padding=True, truncation=True, max_length=512, return_tensors="pt").to(device)

        with torch.no_grad():
            outputs = model(**inputs)
            # Use CLS token or mean pooling
            if hasattr(outputs, "pooler_output") and outputs.pooler_output is not None:
                embeddings = outputs.pooler_output
            else:
                embeddings = outputs.last_hidden_state.mean(dim=1)

        all_embeddings.append(embeddings.cpu().numpy())

    return np.concatenate(all_embeddings, axis=0)


def cluster_by_cosine(embeddings: np.ndarray, threshold: float) -> List[List[int]]:
    """Cluster features by cosine similarity using agglomerative clustering."""
    from scipy.cluster.hierarchy import fcluster, linkage
    from scipy.spatial.distance import squareform

    # Compute cosine similarity matrix
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms = np.maximum(norms, 1e-8)
    normalized = embeddings / norms
    sim_matrix = normalized @ normalized.T

    # Convert to distance
    dist_matrix = 1.0 - sim_matrix
    np.fill_diagonal(dist_matrix, 0)
    dist_matrix = np.maximum(dist_matrix, 0)

    # Agglomerative clustering
    condensed = squareform(dist_matrix, checks=False)
    Z = linkage(condensed, method="average")
    labels = fcluster(Z, t=1.0 - threshold, criterion="distance")

    # Group by cluster
    clusters: Dict[int, List[int]] = {}
    for idx, label in enumerate(labels):
        clusters.setdefault(label, []).append(idx)

    return list(clusters.values())


def select_representatives(
    features: List[dict],
    clusters: List[List[int]],
    embeddings: np.ndarray,
) -> List[int]:
    """Select the feature nearest each cluster centroid."""
    representatives = []

    for cluster_indices in clusters:
        if len(cluster_indices) == 1:
            representatives.append(cluster_indices[0])
            continue

        # Compute centroid
        cluster_embeddings = embeddings[cluster_indices]
        centroid = cluster_embeddings.mean(axis=0)

        # Find nearest to centroid
        norms = np.linalg.norm(cluster_embeddings, axis=1)
        centroid_norm = np.linalg.norm(centroid)
        if centroid_norm < 1e-8:
            representatives.append(cluster_indices[0])
            continue

        similarities = (cluster_embeddings @ centroid) / (norms * centroid_norm + 1e-8)
        best_local_idx = np.argmax(similarities)
        representatives.append(cluster_indices[best_local_idx])

    return sorted(representatives)


def rebuild_taxonomy(full_data: dict, features: List[dict], keep_indices: List[int]) -> dict:
    """Rebuild taxonomy keeping only the selected features."""
    keep_ids = {features[i]["id"] for i in keep_indices}

    old_taxonomy = full_data.get("feature_taxonomy", full_data)
    new_taxonomy = {}

    for dim_key, dim_data in old_taxonomy.items():
        if not isinstance(dim_data, dict):
            continue

        new_dim = {}
        for k, v in dim_data.items():
            if k != "aspects":
                new_dim[k] = v

        new_aspects = {}
        for asp_key, asp_data in dim_data.get("aspects", {}).items():
            kept_features = [f for f in asp_data.get("features", []) if f.get("id") in keep_ids]
            if kept_features:
                new_asp = {k: v for k, v in asp_data.items() if k != "features"}
                new_asp["features"] = kept_features
                new_aspects[asp_key] = new_asp

        if new_aspects:
            new_dim["aspects"] = new_aspects
            new_taxonomy[dim_key] = new_dim

    # Compute metadata
    total = sum(
        len(asp.get("features", []))
        for dim in new_taxonomy.values()
        for asp in dim.get("aspects", {}).values()
    )
    from collections import Counter
    type_counts = Counter()
    dim_counts = {}
    for dim_key, dim_data in new_taxonomy.items():
        dc = 0
        for asp in dim_data.get("aspects", {}).values():
            for f in asp.get("features", []):
                type_counts[f.get("type", "unknown")] += 1
                dc += 1
        dim_counts[dim_key] = dc

    return {
        "taxonomy_metadata": {
            "total_features": total,
            "feature_type_counts": dict(type_counts),
            "dimension_coverage": dim_counts,
        },
        "feature_taxonomy": new_taxonomy,
    }


def main():
    parser = argparse.ArgumentParser(description="Deduplicate features via clustering")
    parser.add_argument("--taxonomy", required=True, help="Path to union taxonomy JSON")
    parser.add_argument("--output-dir", required=True, help="Output directory")
    parser.add_argument("--method", choices=["embedding", "pearson"], default="embedding",
                        help="Clustering method (default: embedding)")
    parser.add_argument("--sim-threshold", type=float, default=0.85,
                        help="Cosine similarity threshold for merging (default: 0.85)")
    parser.add_argument("--embedding-model", default="codefuse-ai/F2LLM-4B",
                        help="HuggingFace model for embeddings")
    parser.add_argument("--batch-size", type=int, default=8, help="Embedding batch size")
    parser.add_argument("--device", default="auto", help="Device for embedding model")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    full_data, features = load_taxonomy_features(args.taxonomy)
    logger.info(f"Loaded {len(features)} features from taxonomy")

    if args.method == "embedding":
        embeddings = compute_embeddings(
            features, args.embedding_model,
            batch_size=args.batch_size, device=args.device,
        )
        np.save(output_dir / "feature_embeddings.npy", embeddings)
        logger.info(f"Embeddings shape: {embeddings.shape}")

        clusters = cluster_by_cosine(embeddings, args.sim_threshold)
        representatives = select_representatives(features, clusters, embeddings)
    else:
        raise NotImplementedError("Pearson method requires --features-dir with applied feature data. "
                                  "Use --method embedding instead.")

    merged_count = len(features) - len(representatives)
    logger.info(f"Clusters: {len(clusters)}, Merged: {merged_count}, "
                f"Retained: {len(representatives)}")

    # Save cluster assignments
    assignments = []
    for cluster_idx, indices in enumerate(clusters):
        rep_idx = None
        for idx in indices:
            if idx in representatives:
                rep_idx = idx
                break
        for idx in indices:
            assignments.append({
                "feature_id": features[idx]["id"],
                "feature_name": features[idx].get("name", ""),
                "cluster_id": cluster_idx,
                "is_representative": idx in representatives,
                "cluster_size": len(indices),
                "representative_id": features[rep_idx]["id"] if rep_idx is not None else None,
            })

    with open(output_dir / "cluster_assignments.json", "w") as f:
        json.dump(assignments, f, indent=2)

    # Rebuild and save deduplicated taxonomy
    deduped = rebuild_taxonomy(full_data, features, representatives)
    with open(output_dir / f"condensed_taxonomy_{args.sim_threshold}.json", "w") as f:
        json.dump(deduped, f, indent=2, ensure_ascii=False)

    meta = deduped["taxonomy_metadata"]
    logger.info(f"Deduplicated taxonomy: {meta['total_features']} features "
                f"across {len(meta['dimension_coverage'])} dimensions")
    logger.info(f"Saved to {output_dir}")


if __name__ == "__main__":
    main()
