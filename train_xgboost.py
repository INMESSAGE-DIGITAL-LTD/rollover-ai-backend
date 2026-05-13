"""
train_xgboost.py
================
Trains one XGBoost binary classifier per betting market target,
using the training CSV built by football_data_fetcher.py.

USAGE
  python train_xgboost.py \
      --input  data/training_data.csv \
      --output models/ \
      --targets over15 over25 over35 under25 under35 btts home_win

OUTPUT
  models/xgb_{target}.joblib    -- saved classifier
  models/metrics.json            -- AUC / accuracy on holdout test set
"""

import argparse
import json
import logging
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, accuracy_score, brier_score_loss
from xgboost import XGBClassifier

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")

FEATURE_COLS = [
    "implied_home",
    "implied_draw",
    "implied_away",
    "implied_over25",
    "implied_under25",
    "league_over25_rate",
    "league_over15_rate",
    "league_btts_rate",
    "league_avg_goals",
    "league_home_win_rate",
    "league_is_high_scoring",
    "league_is_low_scoring",
]

LABEL_MAP = {
    "over15":   "label_over15",
    "over25":   "label_over25",
    "over35":   "label_over35",
    "under25":  "label_under25",
    "under35":  "label_under35",
    "btts":     "label_btts",
    "home_win": "label_home_win",
    "draw":     "label_draw",
    "away_win": "label_away_win",
}


def _enrich_with_dna(df: pd.DataFrame) -> pd.DataFrame:
    """Add league DNA features as columns using league_dna module."""
    try:
        from utils.league_dna import get_league_dna
        dna_rows = []
        for _, row in df.iterrows():
            dna = get_league_dna(row.get("league_name", "Unknown"))
            dna_rows.append({
                "league_over25_rate":    dna.over25_rate,
                "league_over15_rate":    dna.over15_rate,
                "league_btts_rate":      dna.btts_rate,
                "league_avg_goals":      dna.avg_goals_pg,
                "league_home_win_rate":  dna.home_win_rate,
                "league_is_high_scoring": 1 if dna.is_high_scoring else 0,
                "league_is_low_scoring":  1 if dna.is_low_scoring else 0,
            })
        dna_df = pd.DataFrame(dna_rows, index=df.index)
        return pd.concat([df, dna_df], axis=1)
    except ImportError:
        log.warning("league_dna not found -- DNA features will be zeros")
        for col in FEATURE_COLS:
            if col.startswith("league_") and col not in df.columns:
                df[col] = 0.0
        return df


def _prepare_features(df: pd.DataFrame) -> pd.DataFrame:
    """Select + fill feature columns, return clean numeric DataFrame."""
    available = [c for c in FEATURE_COLS if c in df.columns]
    missing = [c for c in FEATURE_COLS if c not in df.columns]
    if missing:
        log.warning("Missing features (will be 0): %s", missing)

    X = df[available].copy()
    for col in missing:
        X[col] = 0.0

    X = X[FEATURE_COLS]
    X = X.apply(pd.to_numeric, errors="coerce").fillna(0.0)
    return X


def train_model(
    df: pd.DataFrame,
    target_col: str,
    target_name: str,
    output_dir: Path,
    test_size: float = 0.20,
) -> dict:
    """Train a single XGBoost model for `target_col`."""
    valid = df[df[target_col].notna()].copy()
    if len(valid) < 200:
        log.warning("Not enough rows for %s (%d) -- skipping", target_name, len(valid))
        return {}

    X = _prepare_features(valid)
    y = valid[target_col].astype(int)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=42, stratify=y
    )

    pos_rate = y_train.mean()
    scale_pos_weight = (1 - pos_rate) / pos_rate if pos_rate > 0 else 1.0

    model = XGBClassifier(
        n_estimators=300,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_weight=3,
        gamma=0.1,
        reg_alpha=0.1,
        reg_lambda=1.0,
        scale_pos_weight=scale_pos_weight,
        eval_metric="logloss",
        early_stopping_rounds=30,
        random_state=42,
        n_jobs=-1,
    )

    model.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        verbose=False,
    )

    y_prob = model.predict_proba(X_test)[:, 1]
    y_pred = (y_prob >= 0.50).astype(int)

    metrics = {
        "target":      target_name,
        "samples":     len(valid),
        "pos_rate":    round(float(pos_rate), 4),
        "auc":         round(float(roc_auc_score(y_test, y_prob)), 4),
        "accuracy":    round(float(accuracy_score(y_test, y_pred)), 4),
        "brier":       round(float(brier_score_loss(y_test, y_prob)), 4),
        "best_iteration": int(model.best_iteration) if hasattr(model, "best_iteration") else 300,
    }
    log.info(
        "OK %s -- AUC=%.3f  ACC=%.3f  Brier=%.3f  (n=%d, pos=%.1f%%)",
        target_name, metrics["auc"], metrics["accuracy"], metrics["brier"],
        len(valid), pos_rate * 100
    )

    output_path = output_dir / f"xgb_{target_name}.joblib"
    joblib.dump(model, output_path)
    log.info("   Saved -> %s", output_path)

    return metrics


def main():
    parser = argparse.ArgumentParser(description="Train XGBoost market models")
    parser.add_argument("--input",   required=True, help="Path to training CSV")
    parser.add_argument("--output",  required=True, help="Directory to save models")
    parser.add_argument(
        "--targets", nargs="+",
        default=list(LABEL_MAP.keys()),
        choices=list(LABEL_MAP.keys()),
        help="Which markets to train",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    log.info("Loading training data from %s ...", input_path)
    df = pd.read_csv(input_path, low_memory=False)
    log.info("Loaded %d rows x %d columns", *df.shape)

    log.info("Enriching with League DNA features ...")
    df = _enrich_with_dna(df)

    all_metrics = []
    for target_name in args.targets:
        label_col = LABEL_MAP[target_name]
        if label_col not in df.columns:
            log.warning("Label column '%s' not found -- skipping %s", label_col, target_name)
            continue
        m = train_model(df, label_col, target_name, output_dir)
        if m:
            all_metrics.append(m)

    metrics_path = output_dir / "metrics.json"
    metrics_path.write_text(json.dumps(all_metrics, indent=2))
    log.info("Saved metrics to %s", metrics_path)

    print("\n" + "=" * 65)
    print(f"{'Target':<15} {'AUC':>6} {'ACC':>6} {'Brier':>7} {'N':>7} {'Pos%':>6}")
    print("-" * 65)
    for m in sorted(all_metrics, key=lambda x: x["auc"], reverse=True):
        print(
            f"{m['target']:<15} {m['auc']:>6.3f} {m['accuracy']:>6.3f} "
            f"{m['brier']:>7.4f} {m['samples']:>7} {m['pos_rate']*100:>5.1f}%"
        )
    print()


if __name__ == "__main__":
    main()
