"""
Generate labels for all markets from historical match data.
Expanded to cover BTTS, result, and double chance markets.
"""
import pandas as pd

def generate_all_labels(match):
    """
    Generate binary labels (0 or 1) for ALL prediction markets.
    
    Input: A single match row with FTHG, FTAG, HTHG, HTAG
    Output: Dictionary with market labels
    """
    ft_home = match['FTHG']
    ft_away = match['FTAG']
    ht_home = match['HTHG']
    ht_away = match['HTAG']
    
    ft_total = ft_home + ft_away
    ht_total = ht_home + ht_away
    sh_home = ft_home - ht_home
    sh_away = ft_away - ht_away
    sh_total = sh_home + sh_away
    
    labels = {}
    
    # Full Time Over/Under
    labels['ft_over_15'] = 1 if ft_total > 1.5 else 0
    labels['ft_under_15'] = 1 if ft_total < 1.5 else 0
    
    # Team-specific FT
    labels['home_over_15'] = 1 if ft_home > 1.5 else 0
    labels['home_under_15'] = 1 if ft_home < 1.5 else 0
    labels['away_over_15'] = 1 if ft_away > 1.5 else 0
    labels['away_under_15'] = 1 if ft_away < 1.5 else 0
    
    # Half Time
    labels['ht_over_15'] = 1 if ht_total > 1.5 else 0
    labels['ht_under_15'] = 1 if ht_total < 1.5 else 0
    
    # First/Second Half 0.5
    labels['fh_over_05'] = 1 if ht_total > 0.5 else 0
    labels['fh_under_05'] = 1 if ht_total < 0.5 else 0
    labels['sh_over_05'] = 1 if sh_total > 0.5 else 0
    labels['sh_under_05'] = 1 if sh_total < 0.5 else 0
    
    # Team 0.5 Goals
    labels['home_over_05'] = 1 if ft_home > 0.5 else 0
    labels['away_over_05'] = 1 if ft_away > 0.5 else 0
    
    # NEW: BTTS
    labels['btts_yes'] = 1 if (ft_home > 0 and ft_away > 0) else 0
    labels['btts_no'] = 1 if (ft_home == 0 or ft_away == 0) else 0
    
    # NEW: Result markets
    labels['home_win'] = 1 if ft_home > ft_away else 0
    labels['draw'] = 1 if ft_home == ft_away else 0
    labels['away_win'] = 1 if ft_away > ft_home else 0
    
    # NEW: Double Chance
    labels['dc_home_draw'] = 1 if ft_home >= ft_away else 0
    labels['dc_away_draw'] = 1 if ft_away >= ft_home else 0
    labels['dc_home_away'] = 1 if ft_home != ft_away else 0
    
    # NEW: Over 2.5 / Under 3.5
    labels['ft_over_25'] = 1 if ft_total > 2.5 else 0
    labels['ft_under_35'] = 1 if ft_total < 3.5 else 0
    
    return labels
