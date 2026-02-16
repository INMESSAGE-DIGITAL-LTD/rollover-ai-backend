"""
Multi-Market Predictor - One model per market
"""
import xgboost as xgb
import pickle
from pathlib import Path

class MultiMarketPredictor:
    """
    Manages 14 separate XGBoost models, one for each market
    """
    def __init__(self):
        self.models = {}
        self.markets = [
            'ft_over_15', 'ft_under_15',
            'home_over_15', 'home_under_15',
            'away_over_15', 'away_under_15',
            'ht_over_15', 'ht_under_15',
            'fh_over_05', 'fh_under_05',
            'sh_over_05', 'sh_under_05',
            'home_over_05', 'away_over_05',
        ]
    
    def train_all_markets(self, X_train, y_labels, X_test, y_test_labels):
        """
        Train one model for each market
        
        Args:
            X_train: Feature matrix (pandas DataFrame)
            y_labels: Dictionary of labels for each market
            X_test: Test features
            y_test_labels: Test labels
        """
        results = {}
        
        for market in self.markets:
            print(f"\n🔄 Training {market}...")
            
            # Get labels for this market
            y_train = y_labels[market]
            y_test = y_test_labels[market]
            
            # Initialize model
            model = xgb.XGBClassifier(
                n_estimators=100,
                max_depth=5,
                learning_rate=0.1,
                objective='binary:logistic',
                random_state=42,
                eval_metric='logloss'
            )
            
            # Train
            model.fit(
                X_train, y_train,
                eval_set=[(X_test, y_test)],
                verbose=False
            )
            
            # Evaluate
            train_acc = model.score(X_train, y_train)
            test_acc = model.score(X_test, y_test)
            
            # Store model
            self.models[market] = model
            
            results[market] = {
                'train_accuracy': train_acc,
                'test_accuracy': test_acc
            }
            
            print(f"   Train Acc: {train_acc:.2%}")
            print(f"   Test Acc:  {test_acc:.2%}")
        
        return results
    
    def predict_match(self, match_features):
        """
        Predict all 14 markets for a single match
        
        Args:
            match_features: dict or DataFrame with feature values
        
        Returns:
            dict: {market: probability}
        """
        import pandas as pd
        
        # Convert to DataFrame if dict
        if isinstance(match_features, dict):
            match_features = pd.DataFrame([match_features])
        
        predictions = {}
        
        for market, model in self.models.items():
            # Get probability of class 1 (YES)
            prob = model.predict_proba(match_features)[0][1]
            predictions[market] = round(prob, 3)
        
        return predictions
    
    def save_models(self, directory='models/trained'):
        """Save all models to disk"""
        Path(directory).mkdir(parents=True, exist_ok=True)
        
        for market, model in self.models.items():
            filepath = f"{directory}/{market}_model.json"
            model.save_model(filepath)
            print(f"✅ Saved {market}")
    
    def load_models(self, directory='models/trained'):
        """Load all models from disk"""
        for market in self.markets:
            filepath = f"{directory}/{market}_model.json"
            model = xgb.XGBClassifier()
            model.load_model(filepath)
            self.models[market] = model
            print(f"✅ Loaded {market}")

# Example usage
if __name__ == '__main__':
    print("Multi-Market Predictor Ready!")
    print(f"Total Markets: 14")
    print("\nMarkets:")
    predictor = MultiMarketPredictor()
    for i, market in enumerate(predictor.markets, 1):
        print(f"  {i}. {market}")
