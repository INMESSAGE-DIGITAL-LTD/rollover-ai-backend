"""
Multi-Market Predictor - One model per market
Enhanced with expanded markets and regularized hyperparameters.
"""
import xgboost as xgb
import pickle
from pathlib import Path

# Original 18 features (backward-compatible with existing trained models)
ORIGINAL_FEATURES = [
    'home_goals_per_game', 'home_goals_conceded_per_game',
    'home_over15_rate', 'home_over05_rate', 'home_first_half_goals',
    'away_goals_per_game', 'away_goals_conceded_per_game',
    'away_over15_rate', 'away_over05_rate', 'away_first_half_goals',
    'home_home_goals', 'home_home_conceded',
    'away_away_goals', 'away_away_conceded',
    'total_expected_goals', 'defensive_strength',
    'over15_odds', 'under15_odds',
]

# Extended features (used when models are retrained)
EXTENDED_FEATURES = ORIGINAL_FEATURES + [
    'home_btts_rate', 'away_btts_rate',
    'home_clean_sheet_rate', 'away_clean_sheet_rate',
    'home_attack_strength', 'away_attack_strength',
    'attack_vs_defense_ratio',
    'home_momentum', 'away_momentum',
    'home_goals_std', 'away_goals_std',
    'home_over25_rate', 'away_over25_rate',
    'home_scored_in_rate', 'away_scored_in_rate',
]

# Original 14 markets
ORIGINAL_MARKETS = [
    'ft_over_15', 'ft_under_15',
    'home_over_15', 'home_under_15',
    'away_over_15', 'away_under_15',
    'ht_over_15', 'ht_under_15',
    'fh_over_05', 'fh_under_05',
    'sh_over_05', 'sh_under_05',
    'home_over_05', 'away_over_05',
]

# Expanded markets (new models after retraining)
EXPANDED_MARKETS = ORIGINAL_MARKETS + [
    'btts_yes', 'btts_no',
    'home_win', 'draw', 'away_win',
    'dc_home_draw', 'dc_away_draw', 'dc_home_away',
    'ft_over_25', 'ft_under_35',
]


class MultiMarketPredictor:
    def __init__(self):
        self.models = {}
        self.markets = ORIGINAL_MARKETS
        self.feature_names = ORIGINAL_FEATURES
        self._extended = False
    
    def train_all_markets(self, X_train, y_labels, X_test, y_test_labels):
        """Train one regularized XGBoost model for each market."""
        # Detect if extended features are available
        available_markets = [m for m in EXPANDED_MARKETS if m in y_labels]
        self.markets = available_markets
        
        if X_train.shape[1] > 18:
            self.feature_names = EXTENDED_FEATURES[:X_train.shape[1]]
            self._extended = True
        
        results = {}
        
        for market in self.markets:
            print(f"\n🔄 Training {market}...")
            
            y_train = y_labels[market]
            y_test = y_test_labels[market]
            
            # Regularized hyperparameters to reduce overfitting
            model = xgb.XGBClassifier(
                n_estimators=200,
                max_depth=4,
                learning_rate=0.05,
                min_child_weight=5,
                subsample=0.8,
                colsample_bytree=0.8,
                reg_alpha=0.1,
                reg_lambda=1.0,
                objective='binary:logistic',
                random_state=42,
                eval_metric='logloss',
                early_stopping_rounds=20,
            )
            
            model.fit(
                X_train, y_train,
                eval_set=[(X_test, y_test)],
                verbose=False,
            )
            
            train_acc = model.score(X_train, y_train)
            test_acc = model.score(X_test, y_test)
            
            self.models[market] = model
            
            results[market] = {
                'train_accuracy': train_acc,
                'test_accuracy': test_acc,
            }
            
            print(f"   Train: {train_acc:.2%}  Test: {test_acc:.2%}")
        
        return results
    
    def predict_match(self, match_features):
        """Predict all markets for a single match using native Booster API."""
        import numpy as np
        
        # Use the feature set matching the loaded models
        feature_order = self.feature_names
        
        if isinstance(match_features, dict):
            # Fill missing extended features with defaults
            values = []
            for f in feature_order:
                values.append(match_features.get(f, 0.5))
            match_array = np.array([values], dtype=np.float32)
        else:
            match_array = np.array(match_features, dtype=np.float32)
        
        dmatrix = xgb.DMatrix(match_array, feature_names=feature_order)
        
        predictions = {}
        for market, model in self.models.items():
            prob = model.predict(dmatrix)[0]
            predictions[market] = round(float(prob), 3)
        
        return predictions
    
    def save_models(self, directory='models/trained'):
        """Save all models to disk."""
        Path(directory).mkdir(parents=True, exist_ok=True)
        
        for market, model in self.models.items():
            filepath = f"{directory}/{market}_model.json"
            model.save_model(filepath)
            print(f"✅ Saved {market}")
        
        # Save metadata
        import json
        meta = {
            'markets': self.markets,
            'feature_names': self.feature_names,
            'extended': self._extended,
        }
        with open(f"{directory}/model_meta.json", 'w') as f:
            json.dump(meta, f)
    
    def load_models(self, directory='models/trained'):
        """Load all models from disk, with backward compatibility."""
        import json
        
        meta_path = f"{directory}/model_meta.json"
        if Path(meta_path).exists():
            with open(meta_path) as f:
                meta = json.load(f)
            self.markets = meta.get('markets', ORIGINAL_MARKETS)
            self.feature_names = meta.get('feature_names', ORIGINAL_FEATURES)
            self._extended = meta.get('extended', False)
        else:
            self.markets = ORIGINAL_MARKETS
            self.feature_names = ORIGINAL_FEATURES
        
        loaded = []
        for market in self.markets:
            filepath = f"{directory}/{market}_model.json"
            if Path(filepath).exists():
                model = xgb.Booster()
                model.load_model(filepath)
                self.models[market] = model
                loaded.append(market)
        
        print(f"✅ Loaded {len(loaded)} models ({len(self.feature_names)} features)")
