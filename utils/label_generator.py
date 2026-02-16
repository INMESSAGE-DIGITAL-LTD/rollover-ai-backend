"""
Generate labels for all markets from historical match data
"""
import pandas as pd

def generate_all_labels(match):
    """
    Generate binary labels (0 or 1) for ALL 14 markets
    
    Input: A single match row with columns:
        - FTHG: Full Time Home Goals
        - FTAG: Full Time Away Goals  
        - HTHG: Half Time Home Goals
        - HTAG: Half Time Away Goals
    
    Output: Dictionary with 14 market labels
    """
    # Extract goals
    ft_home = match['FTHG']
    ft_away = match['FTAG']
    ht_home = match['HTHG']
    ht_away = match['HTAG']
    
    # Calculate totals
    ft_total = ft_home + ft_away
    ht_total = ht_home + ht_away
    
    # Second half goals
    sh_home = ft_home - ht_home
    sh_away = ft_away - ht_away
    sh_total = sh_home + sh_away
    
    labels = {}
    
    # Full Time Markets
    labels['ft_over_15'] = 1 if ft_total > 1.5 else 0
    labels['ft_under_15'] = 1 if ft_total < 1.5 else 0
    
    # Team-specific FT Markets
    labels['home_over_15'] = 1 if ft_home > 1.5 else 0
    labels['home_under_15'] = 1 if ft_home < 1.5 else 0
    labels['away_over_15'] = 1 if ft_away > 1.5 else 0
    labels['away_under_15'] = 1 if ft_away < 1.5 else 0
    
    # Half Time Markets
    labels['ht_over_15'] = 1 if ht_total > 1.5 else 0
    labels['ht_under_15'] = 1 if ht_total < 1.5 else 0
    
    # First Half Markets (same as HT for full-time matches)
    labels['fh_over_05'] = 1 if ht_total > 0.5 else 0
    labels['fh_under_05'] = 1 if ht_total < 0.5 else 0
    
    # Second Half Markets
    labels['sh_over_05'] = 1 if sh_total > 0.5 else 0
    labels['sh_under_05'] = 1 if sh_total < 0.5 else 0
    
    # 0.5 Goals Home/Away
    labels['home_over_05'] = 1 if ft_home > 0.5 else 0
    labels['away_over_05'] = 1 if ft_away > 0.5 else 0
    
    return labels

# Example usage
if __name__ == '__main__':
    # Test with sample match: Man City 3-1 Arsenal (HT: 2-0)
    sample_match = {
        'FTHG': 3,
        'FTAG': 1,
        'HTHG': 2,
        'HTAG': 0
    }
    
    labels = generate_all_labels(sample_match)
    
    print("Man City 3-1 Arsenal (HT: 2-0)\n")
    print("Market Predictions:")
    print("-" * 50)
    for market, label in labels.items():
        result = "✅ YES" if label == 1 else "❌ NO"
        print(f"{market:20} → {result}")
