"""
Train all market prediction models with enhanced features and regularization.
Supports expanded markets (BTTS, result, double chance, over 2.5).
Uses time-based split to avoid data leakage.
"""
import sys
sys.path.append('..')

import pandas as pd
import numpy as np
from pathlib import Path
from models.multi_market_predictor import MultiMarketPredictor
from utils.label_generator import generate_all_labels
from utils.feature_calculator import prepare_dataset

def prepare_labels(matches):
    """Generate labels for all markets including expanded ones."""
    print("🔄 Generating labels for all markets...")
    
    sample_labels = generate_all_labels(matches[0])
    all_labels = {market: [] for market in sample_labels.keys()}
    
    for match in matches:
        labels = generate_all_labels(match)
        for market, label in labels.items():
            all_labels[market].append(label)
    
    print(f"✅ {len(all_labels)} markets generated")
    
    print("\n📊 Label Distribution:")
    for market, labels in all_labels.items():
        pos_rate = sum(labels) / len(labels) * 100
        print(f"   {market:20} → {pos_rate:.1f}% YES")
    
    return all_labels

def main():
    print("🚀 Enhanced Model Training")
    print("   (Expanded features + markets + regularization)")
    print("=" * 60)
    
    # Load data
    print("\n1️⃣ Loading data...")
    data_file = Path('../data/raw/all_matches.csv')
    df = pd.read_csv(data_file, low_memory=False)
    print(f"✅ Loaded {len(df)} matches")
    
    if 'League' in df.columns:
        print(f"   Leagues: {df['League'].nunique()}")
        for league, count in df['League'].value_counts().items():
            print(f"   - {league}: {count}")
    
    # Prepare features
    print("\n2️⃣ Calculating enhanced pre-match features...")
    X, match_rows = prepare_dataset(df)
    print(f"✅ {len(X)} matches with {X.shape[1]} features")
    
    # Generate labels
    print("\n3️⃣ Generating labels...")
    y_labels = prepare_labels(match_rows)
    
    # Time-based split (80/20) — preserves temporal order
    print("\n4️⃣ Time-based split (80/20)...")
    split_idx = int(len(X) * 0.8)
    
    X_train = X[:split_idx].reset_index(drop=True)
    X_test = X[split_idx:].reset_index(drop=True)
    
    y_train_labels = {}
    y_test_labels = {}
    
    for market, labels in y_labels.items():
        labels_array = np.array(labels)
        y_train_labels[market] = labels_array[:split_idx]
        y_test_labels[market] = labels_array[split_idx:]
    
    print(f"✅ Train: {len(X_train)} matches")
    print(f"✅ Test:  {len(X_test)} matches")
    
    # Train models
    print("\n5️⃣ Training XGBoost models (regularized)...")
    print("=" * 60)
    
    predictor = MultiMarketPredictor()
    results = predictor.train_all_markets(X_train, y_train_labels, X_test, y_test_labels)
    
    # Results
    print("\n" + "=" * 60)
    print("📊 TRAINING RESULTS")
    print("=" * 60)
    
    total_train_acc = 0
    total_test_acc = 0
    
    for market, metrics in results.items():
        train_acc = metrics['train_accuracy'] * 100
        test_acc = metrics['test_accuracy'] * 100
        total_train_acc += train_acc
        total_test_acc += test_acc
        gap = train_acc - test_acc
        flag = " ⚠️" if gap > 10 else ""
        print(f"{market:20} → Train: {train_acc:.1f}%  Test: {test_acc:.1f}%  Gap: {gap:.1f}%{flag}")
    
    n_markets = len(results)
    avg_train = total_train_acc / n_markets
    avg_test = total_test_acc / n_markets
    
    print("=" * 60)
    print(f"AVERAGE → Train: {avg_train:.1f}%  Test: {avg_test:.1f}%  Gap: {avg_train - avg_test:.1f}%")
    print(f"MARKETS: {n_markets}  FEATURES: {X.shape[1]}")
    print("=" * 60)
    
    # Save models
    print("\n6️⃣ Saving models...")
    predictor.save_models('../models/trained')
    
    print(f"\n✅ TRAINING COMPLETE!")
    print(f"✅ {n_markets} models saved to: models/trained/")
    print(f"✅ Average test accuracy: {avg_test:.1f}%")
    
    if avg_test >= 65:
        print("🎉 EXCELLENT! Models are production-ready!")
    elif avg_test >= 55:
        print("✅ GOOD! Models are usable for hybrid engine")
    else:
        print("⚠️ Consider adding more training data")

if __name__ == '__main__':
    main()
