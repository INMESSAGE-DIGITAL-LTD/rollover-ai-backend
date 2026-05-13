"""
evaluate_models.py
==================
Evaluates trained XGBoost models on a holdout test set and prints a
metrics summary. Called by the weekly retrain workflow after training.

USAGE
  python evaluate_models.py \
      --data   data/training_data.csv \
      --models models/
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
}


def _enrich_with_dna(df: pd.DataFrame) -> pd.DataFrame:
    try:
        from utils.league_dna import get_league_dna
        rows = []
        for _, row in df.iterrows():
            dna = get_league_dna(row.get("league_name", "Unknown"))
            rows.append({
                "league_over25_rate":     dna.over25_rate,
                "league_over15_rate":     dna.over15_rate,
                "league_btts_rate":       dna.btts_rate,
                "league_avg_goals":       dna.avg_goals_pg,
                "league_home_win_rate":   dna.home_win_rate,
                "league_is_high_scoring": 1 if dna.is_high_scoring else 0,
                "league_is_low_scoring":  1 if dna.is_low_scoring else 0,
            })
        return pd.concat([df, pd.DataFrame(rows, index=df.index)], axis=1)
    except ImportError:
        for col in FEATURE_COLS:
            if col.startswith("league_") and col not in df.columns:
                df[col] = 0.0
        return df


def evaluate(data_path: Path, models_dir: Path) -> list:
    log.info("Loading data from %s ...", data_path)
    df = pd.read_csv(data_path, low_memory=False)
    log.info("Loaded %d rows", len(df))

    log.info("Enriching with League DNA ...")
    df = _enrich_with_dna(df)

    available = [c for c in FEATURE_COLS if c in df.columns]
    missing   = [c for c in FEATURE_COLS if c not in df.columns]
    for col in missing:
        df[col] = 0.0

    results = []

    for target, label_col in LABEL_MAP.items():
        model_path = models_dir / f"xgb_{target}.joblib"
        if not model_path.exists():
            log.warning("Model not found: %s — skipping", model_path)
            continue
        if label_col not in df.columns:
            log.warning("Label '%s' missing — skipping %s", label_col, target)
            continue

        valid = df[df[label_col].notna()].copy()
        X = valid[FEATURE_COLS].apply(pd.to_numeric, errors="coerce").fillna(0.0)
        y = valid[label_col].astype(int)

        _, X_test, _, y_test = train_test_split(
            X, y, test_size=0.20, random_state=42, stratify=y
        )

        model   = joblib.load(model_path)
        y_prob  = model.predict_proba(X_test)[:, 1]
        y_pred  = (y_prob >= 0.50).astype(int)

        auc      = roc_auc_score(y_test, y_prob)
        acc      = accuracy_score(y_test, y_pred)
        brier    = brier_score_loss(y_test, y_prob)
        pos_rate = y.mean()

        results.append({
            "target":   target,
            "samples":  len(valid),
            "pos_rate": round(float(pos_rate), 4),
            "auc":      round(float(auc),  4),
            "accuracy": round(float(acc),  4),
            "brier":    round(float(brier), 4),
        })

        log.info(
            "%-10s  AUC=%.3f  ACC=%.3f  Brier=%.4f  (n=%d, pos=%.1f%%)",
            target, auc, acc, brier, len(valid), pos_rate * 100,
        )

    return results


def main():
    parser = argparse.ArgumentParser(description="Evaluate trained XGBoost models")
    parser.add_argument("--data",   required=True, help="Path to training CSV")
    parser.add_argument("--models", required=True, help="Directory containing xgb_*.joblib files")
    args = parser.parse_args()

    results = evaluate(Path(args.data), Path(args.models))

    if not results:
        log.error("No models evaluated.")
        raise SystemExit(1)

    print("\n" + "=" * 68)
    print(f"{'Target':<12} {'AUC':>6} {'ACC':>6} {'Brier':>7} {'N':>7} {'Pos%':>6}")
    print("-" * 68)
    for r in sorted(results, key=lambda x: x["auc"], reverse=True):
        flag = " ⚠️" if r["auc"] < 0.55 else ""
        print(
            f"{r['target']:<12} {r['auc']:>6.3f} {r['accuracy']:>6.3f} "
            f"{r['brier']:>7.4f} {r['samples']:>7} {r['pos_rate']*100:>5.1f}%{flag}"
        )
    print()

    out = Path(args.models) / "eval_report.json"
    out.write_text(json.dumps(results, indent=2))
    log.info("Saved evaluation report to %s", out)


if __name__ == "__main__":
    main()
