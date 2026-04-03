#!/usr/bin/env python3
"""
Stage 6b: Bootstrap SHAP stability analysis for feature importance.

Tests whether features with high importance are stable across bootstrap runs.
Assigns features to roles: core (universal human/AI markers) and fingerprint
(source-specific cues).

Usage:
    python -m storyscope.6_classification.shap_analysis \
        --features data/storyscope_features.parquet \
        --taxonomy data/taxonomy.json \
        --output-dir outputs/shap \
        --task both \
        --bootstrap 50
"""

from __future__ import annotations

import argparse
import json
import logging
import warnings
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap
from scipy.stats import spearmanr
from sklearn.model_selection import GroupKFold
from xgboost import XGBClassifier

from storyscope.utils.feature_encoder import (
    build_feature_type_map,
    encode_features,
    filter_matched_prompts,
    build_groups,
    friendly_col_name,
    get_taxonomy_feature_ids,
    load_features_parquet,
    load_taxonomy,
    make_binary_target,
    make_multiclass_target,
)

warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

MISSING = "__MISSING__"


def run_bootstrap_shap(
    X: np.ndarray,
    y: np.ndarray,
    groups: np.ndarray,
    col_names: List[str],
    n_bootstrap: int = 50,
    task: str = "binary",
    n_estimators: int = 420,
    max_depth: int = 8,
    human_weight: float = 5.0,
    n_classes: int = 2,
) -> Tuple[np.ndarray, List[np.ndarray]]:
    """
    Run bootstrap SHAP analysis.

    Returns:
        mean_importance: (n_features,) mean |SHAP| across bootstraps
        all_importances: list of (n_features,) arrays per bootstrap
    """
    unique_groups = np.unique(groups)
    all_importances = []

    for b in range(n_bootstrap):
        # Resample groups (prompt-level)
        rng = np.random.RandomState(b)
        boot_groups = rng.choice(unique_groups, size=len(unique_groups), replace=True)
        boot_mask = np.isin(groups, boot_groups)
        X_boot, y_boot = X[boot_mask], y[boot_mask]

        if task == "binary":
            sample_weights = np.where(y_boot == 1, human_weight, 1.0)
            clf = XGBClassifier(
                n_estimators=n_estimators, max_depth=max_depth,
                use_label_encoder=False, eval_metric="logloss",
                random_state=b,
            )
        else:
            human_idx = 0  # assumes human is first class
            sample_weights = np.where(y_boot == human_idx, human_weight, 1.0)
            clf = XGBClassifier(
                n_estimators=n_estimators, max_depth=max_depth,
                objective="multi:softmax", num_class=n_classes,
                use_label_encoder=False, eval_metric="mlogloss",
                random_state=b,
            )

        clf.fit(X_boot, y_boot, sample_weight=sample_weights)
        explainer = shap.TreeExplainer(clf)
        shap_values = explainer.shap_values(X_boot)

        if isinstance(shap_values, list):
            # Multiclass: average absolute SHAP across classes
            importance = np.mean([np.abs(sv).mean(axis=0) for sv in shap_values], axis=0)
        else:
            importance = np.abs(shap_values).mean(axis=0)

        all_importances.append(importance)

        if (b + 1) % 10 == 0:
            logger.info(f"  Bootstrap {b + 1}/{n_bootstrap}")

    mean_importance = np.mean(all_importances, axis=0)
    return mean_importance, all_importances


def compute_stability(all_importances: List[np.ndarray], top_k: int = 30) -> dict:
    """Compute stability metrics for feature importance rankings."""
    n_bootstrap = len(all_importances)
    n_features = all_importances[0].shape[0]

    # Rank correlation between consecutive bootstraps
    rank_correlations = []
    for i in range(1, n_bootstrap):
        rho, _ = spearmanr(all_importances[i - 1], all_importances[i])
        rank_correlations.append(rho)

    # Top-k stability: fraction of top-k features consistent across bootstraps
    top_k_sets = []
    for imp in all_importances:
        top_k_sets.append(set(np.argsort(imp)[-top_k:]))

    pairwise_overlaps = []
    for i in range(n_bootstrap):
        for j in range(i + 1, n_bootstrap):
            overlap = len(top_k_sets[i] & top_k_sets[j]) / top_k
            pairwise_overlaps.append(overlap)

    return {
        "mean_rank_correlation": float(np.mean(rank_correlations)),
        "std_rank_correlation": float(np.std(rank_correlations)),
        f"top_{top_k}_stability": float(np.mean(pairwise_overlaps)),
    }


def save_feature_rankings(
    mean_importance: np.ndarray,
    all_importances: List[np.ndarray],
    col_names: List[str],
    feature_type_map: Dict,
    output_dir: Path,
    task: str,
):
    """Save ranked feature importance with stability metrics."""
    std_importance = np.std(all_importances, axis=0)
    rankings = []

    for idx in np.argsort(mean_importance)[::-1]:
        rankings.append({
            "rank": len(rankings) + 1,
            "encoded_col": col_names[idx],
            "friendly_name": friendly_col_name(col_names[idx], feature_type_map),
            "mean_shap": float(mean_importance[idx]),
            "std_shap": float(std_importance[idx]),
            "cv": float(std_importance[idx] / max(mean_importance[idx], 1e-10)),
        })

    with open(output_dir / f"{task}_feature_rankings.json", "w") as f:
        json.dump(rankings, f, indent=2)

    # Plot top 30
    top_n = min(30, len(rankings))
    fig, ax = plt.subplots(figsize=(10, 8))
    names = [r["friendly_name"][:40] for r in rankings[:top_n]]
    values = [r["mean_shap"] for r in rankings[:top_n]]
    errors = [r["std_shap"] for r in rankings[:top_n]]

    ax.barh(range(top_n), values[::-1], xerr=errors[::-1], capsize=3)
    ax.set_yticks(range(top_n))
    ax.set_yticklabels(names[::-1], fontsize=8)
    ax.set_xlabel("Mean |SHAP|")
    ax.set_title(f"Top {top_n} Features ({task})")
    plt.tight_layout()
    fig.savefig(output_dir / f"{task}_top_features.png", dpi=150)
    plt.close(fig)

    logger.info(f"  Saved rankings and plot to {output_dir}")


def main():
    parser = argparse.ArgumentParser(description="Bootstrap SHAP stability analysis")
    parser.add_argument("--features", required=True, help="Path to features parquet or directory")
    parser.add_argument("--taxonomy", required=True, help="Path to taxonomy JSON")
    parser.add_argument("--output-dir", required=True, help="Output directory")
    parser.add_argument("--task", choices=["binary", "multiclass", "both"], default="both")
    parser.add_argument("--bootstrap", type=int, default=50, help="Number of bootstrap iterations")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    taxonomy = load_taxonomy(args.taxonomy)
    feature_ids = get_taxonomy_feature_ids(taxonomy)
    feature_type_map = build_feature_type_map(taxonomy)

    if args.features.endswith(".parquet"):
        df, _, authors = load_features_parquet(args.features, taxonomy)
    else:
        from storyscope.utils.feature_encoder import load_features_matrix
        df, _, authors = load_features_matrix(args.features, taxonomy)

    df = filter_matched_prompts(df, authors)
    X, col_names = encode_features(df, feature_ids, feature_type_map, mode="multi_hot")
    groups = build_groups(df)

    logger.info(f"Data: {X.shape[0]} samples, {X.shape[1]} encoded features, "
                f"{len(np.unique(groups))} prompts")

    tasks_to_run = []
    if args.task in ("binary", "both"):
        tasks_to_run.append("binary")
    if args.task in ("multiclass", "both"):
        tasks_to_run.append("multiclass")

    for task in tasks_to_run:
        logger.info(f"\n=== {task.upper()} SHAP Analysis ({args.bootstrap} bootstraps) ===")

        if task == "binary":
            y = make_binary_target(df)
            n_classes = 2
        else:
            y, _ = make_multiclass_target(df, authors)
            n_classes = len(authors)

        mean_imp, all_imp = run_bootstrap_shap(
            X, y, groups, col_names,
            n_bootstrap=args.bootstrap,
            task=task,
            n_classes=n_classes,
        )

        stability = compute_stability(all_imp)
        logger.info(f"  Stability: rank_corr={stability['mean_rank_correlation']:.3f}, "
                     f"top_30={stability['top_30_stability']:.3f}")

        save_feature_rankings(mean_imp, all_imp, col_names, feature_type_map, output_dir, task)

        # Save stability report
        with open(output_dir / f"{task}_stability.json", "w") as f:
            json.dump(stability, f, indent=2)


if __name__ == "__main__":
    main()
