"""
Train all 14 market prediction models with PROPER pre-match features
"""
import sys
sys.path.append('..')

import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.model_selection import train_test_split
from models.multi_market_predictor import MultiMarketPredictor
from utils.label_generator import generate_all_labels
from utils.feature_calculator import prepare_dataset

def prepare_labels(matches):
    """
    Generate labels for all 14 markets
    """
    print("🔄 Generating labels for 14 markets...")
    
    all_labels = {market: [] for market in [
        'ft_over_15', 'ft_under_15',
        'home_over_15', 'home_under_15',
        'away_over_15', 'away_under_15',
        'ht_over_15', 'ht_under_15',
        'fh_over_05', 'fh_under_05',
        'sh_over_05', 'sh_under_05',
        'home_over_05', 'away_over_05',
    ]}
    
    for match in matches:
        labels = generate_all_labels(match)
        for market, label in labels.items():
            all_labels[market].append(label)
    
    print(f"✅ Labels generated")
    
    # Print distribution
    print("\n📊 Label Distribution:")
    for market, labels in all_labels.items():
        pos_rate = sum(labels) / len(labels) * 100
        print(f"   {market:20} → {pos_rate:.1f}% YES")
    
    return all_labels

def main():
    print("🚀 Starting PROPER Model Training")
    print("   (Using only PRE-MATCH features)")
    print("=" * 60)
    
    # Load data
    print("\n1️⃣ Loading data...")
    data_file = Path('../data/raw/all_matches.csv')
    df = pd.read_csv(data_file, low_memory=False)
    print(f"✅ Loaded {len(df)} matches")
    
    # Prepare features (pre-match only!)
    print("\n2️⃣ Calculating pre-match features...")
    X, match_rows = prepare_dataset(df)
    print(f"✅ {len(X)} matches with complete feature history")
    
    # Generate labels
    print("\n3️⃣ Generating labels...")
    y_labels = prepare_labels(match_rows)
    
    # Split data
    print("\n4️⃣ Splitting train/test (80/20)...")
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
    print(f"✅ Test: {len(X_test)} matches")
    
    # Train models
    print("\n5️⃣ Training 14 XGBoost models...")
    print("=" * 60)
    
    predictor = MultiMarketPredictor()
    results = predictor.train_all_markets(X_train, y_train_labels, X_test, y_test_labels)
    
    # Print results
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
        print(f"{market:20} → Train: {train_acc:.1f}%  Test: {test_acc:.1f}%")
    
    avg_train = total_train_acc / 14
    avg_test = total_test_acc / 14
    
    print("=" * 60)
    print(f"AVERAGE ACCURACY → Train: {avg_train:.1f}%  Test: {avg_test:.1f}%")
    print("=" * 60)
    
    # Save models
    print("\n6️⃣ Saving models...")
    predictor.save_models('../models/trained')
    
    print("\n✅ TRAINING COMPLETE!")
    print(f"✅ 14 models saved to: models/trained/")
    print(f"✅ Average test accuracy: {avg_test:.1f}%")
    
    if avg_test >= 65:
        print("🎉 EXCELLENT! Models are production-ready!")
    elif avg_test >= 55:
        print("✅ GOOD! Models need some tuning but usable")
    else:
        print("⚠️ Need more training data or better features")

if __name__ == '__main__':
    main()
