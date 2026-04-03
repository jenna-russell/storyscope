#!/usr/bin/env python3
"""
Stage 6a: Train XGBoost classifiers on narrative features.

Trains binary (human vs AI) and/or 6-way (per-source) classifiers using
encoded feature vectors with prompt-level grouping to prevent train/test leakage.

Usage:
    python -m storyscope.6_classification.train_classifier \
        --features data/storyscope_features.parquet \
        --taxonomy data/taxonomy.json \
        --output-dir outputs/classification \
        --task both
"""

from __future__ import annotations

import argparse
import json
import logging
import warnings
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score, classification_report, confusion_matrix,
    f1_score, precision_recall_curve, average_precision_score,
)
from sklearn.model_selection import GroupKFold
from xgboost import XGBClassifier

from storyscope.utils.feature_encoder import (
    build_feature_type_map,
    encode_features,
    filter_matched_prompts,
    build_groups,
    get_taxonomy_feature_ids,
    load_features_parquet,
    load_taxonomy,
    make_binary_target,
    make_multiclass_target,
)

warnings.filterwarnings("ignore", category=UserWarning)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def load_data(features_path: str, taxonomy_path: str, split_col: str = "split"):
    """Load features and taxonomy, split into train/test."""
    taxonomy = load_taxonomy(taxonomy_path)
    feature_ids = get_taxonomy_feature_ids(taxonomy)
    feature_type_map = build_feature_type_map(taxonomy)

    if features_path.endswith(".parquet"):
        df, _, authors = load_features_parquet(features_path, taxonomy)
    else:
        from storyscope.utils.feature_encoder import load_features_matrix
        df, _, authors = load_features_matrix(features_path, taxonomy)

    # Filter to matched prompts (all sources present)
    df = filter_matched_prompts(df, authors)
    logger.info(f"Matched prompts: {df['story_title'].nunique()} prompts, {len(df)} rows, "
                f"{len(authors)} sources")

    return df, feature_ids, feature_type_map, authors


def train_binary(
    df: pd.DataFrame,
    feature_ids: List[str],
    feature_type_map: Dict,
    output_dir: Path,
    n_estimators: int = 420,
    max_depth: int = 8,
    reg_lambda: float = 2.0,
    human_weight: float = 5.0,
):
    """Train binary human-vs-AI classifier."""
    logger.info("=== Binary Classification (Human vs AI) ===")

    X, col_names = encode_features(df, feature_ids, feature_type_map, mode="multi_hot")
    y = make_binary_target(df)
    groups = build_groups(df)

    # Prompt-level train/test split via GroupKFold
    gkf = GroupKFold(n_splits=5)
    train_idx, test_idx = next(gkf.split(X, y, groups))

    X_train, X_test = X[train_idx], X[test_idx]
    y_train, y_test = y[train_idx], y[test_idx]

    # Sample weights: upweight human class
    sample_weights = np.where(y_train == 1, human_weight, 1.0)

    clf = XGBClassifier(
        n_estimators=n_estimators,
        max_depth=max_depth,
        reg_lambda=reg_lambda,
        use_label_encoder=False,
        eval_metric="logloss",
        random_state=42,
    )
    clf.fit(X_train, y_train, sample_weight=sample_weights)

    y_pred = clf.predict(X_test)
    y_prob = clf.predict_proba(X_test)[:, 1]

    # Metrics
    report = classification_report(y_test, y_pred, target_names=["AI", "Human"], output_dict=True)
    macro_f1 = f1_score(y_test, y_pred, average="macro")
    auprc = average_precision_score(y_test, y_prob)

    logger.info(f"  Macro F1: {macro_f1:.4f}")
    logger.info(f"  AUPRC: {auprc:.4f}")
    logger.info(f"  Accuracy: {accuracy_score(y_test, y_pred):.4f}")

    # Save model
    binary_dir = output_dir / "binary"
    binary_dir.mkdir(parents=True, exist_ok=True)
    clf.save_model(str(binary_dir / "model.json"))

    # Save metadata
    meta = {
        "task": "binary",
        "n_train": len(y_train),
        "n_test": len(y_test),
        "n_features_encoded": X.shape[1],
        "macro_f1": float(macro_f1),
        "auprc": float(auprc),
        "classification_report": report,
        "hyperparameters": {
            "n_estimators": n_estimators,
            "max_depth": max_depth,
            "reg_lambda": reg_lambda,
            "human_weight": human_weight,
        },
    }
    (binary_dir / "metadata.json").write_text(json.dumps(meta, indent=2))
    logger.info(f"  Saved to {binary_dir}")

    return clf, col_names


def train_multiclass(
    df: pd.DataFrame,
    feature_ids: List[str],
    feature_type_map: Dict,
    authors: List[str],
    output_dir: Path,
    n_estimators: int = 500,
    max_depth: int = 7,
    reg_lambda: float = 1.0,
    human_weight: float = 5.0,
):
    """Train 6-way multiclass classifier."""
    logger.info("=== Multiclass Classification (6-way) ===")

    X, col_names = encode_features(df, feature_ids, feature_type_map, mode="multi_hot")
    y, label_map = make_multiclass_target(df, authors)
    groups = build_groups(df)

    gkf = GroupKFold(n_splits=5)
    train_idx, test_idx = next(gkf.split(X, y, groups))

    X_train, X_test = X[train_idx], X[test_idx]
    y_train, y_test = y[train_idx], y[test_idx]

    # Sample weights
    human_idx = label_map.get("human", -1)
    sample_weights = np.where(y_train == human_idx, human_weight, 1.0)

    clf = XGBClassifier(
        n_estimators=n_estimators,
        max_depth=max_depth,
        reg_lambda=reg_lambda,
        objective="multi:softmax",
        num_class=len(authors),
        use_label_encoder=False,
        eval_metric="mlogloss",
        random_state=42,
    )
    clf.fit(X_train, y_train, sample_weight=sample_weights)

    y_pred = clf.predict(X_test)

    report = classification_report(y_test, y_pred, target_names=authors, output_dict=True)
    macro_f1 = f1_score(y_test, y_pred, average="macro")

    logger.info(f"  Macro F1: {macro_f1:.4f}")
    logger.info(f"  Accuracy: {accuracy_score(y_test, y_pred):.4f}")

    # Save
    mc_dir = output_dir / "multiclass"
    mc_dir.mkdir(parents=True, exist_ok=True)
    clf.save_model(str(mc_dir / "model.json"))

    meta = {
        "task": "multiclass",
        "n_train": len(y_train),
        "n_test": len(y_test),
        "n_features_encoded": X.shape[1],
        "n_classes": len(authors),
        "label_map": label_map,
        "macro_f1": float(macro_f1),
        "classification_report": report,
        "hyperparameters": {
            "n_estimators": n_estimators,
            "max_depth": max_depth,
            "reg_lambda": reg_lambda,
            "human_weight": human_weight,
        },
    }
    (mc_dir / "metadata.json").write_text(json.dumps(meta, indent=2))
    logger.info(f"  Saved to {mc_dir}")

    return clf, col_names


def main():
    parser = argparse.ArgumentParser(description="Train XGBoost classifiers on narrative features")
    parser.add_argument("--features", required=True, help="Path to features parquet or directory")
    parser.add_argument("--taxonomy", required=True, help="Path to taxonomy JSON")
    parser.add_argument("--output-dir", required=True, help="Output directory")
    parser.add_argument("--task", choices=["binary", "multiclass", "both"], default="both",
                        help="Classification task (default: both)")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    df, feature_ids, feature_type_map, authors = load_data(args.features, args.taxonomy)

    if args.task in ("binary", "both"):
        train_binary(df, feature_ids, feature_type_map, output_dir)

    if args.task in ("multiclass", "both"):
        train_multiclass(df, feature_ids, feature_type_map, authors, output_dir)


if __name__ == "__main__":
    main()
