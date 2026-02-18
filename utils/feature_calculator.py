"""
Calculate pre-match features from historical data.
Enhanced with attack/defense ratios, form momentum, BTTS, and derived stats.
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

class FeatureCalculator:
    def __init__(self, df):
        self.df = df.copy()
        self.df['Date'] = pd.to_datetime(self.df['Date'], format='%d/%m/%Y', errors='coerce')
        self.df = self.df.sort_values('Date')
        
    def get_team_stats(self, team, before_date, last_n=10, home_only=False, away_only=False):
        mask = self.df['Date'] < before_date
        
        if home_only:
            matches = self.df[mask & (self.df['HomeTeam'] == team)]
            goals_for = matches['FTHG']
            goals_against = matches['FTAG']
            first_half_goals = matches['HTHG']
            first_half_against = matches['HTAG']
        elif away_only:
            matches = self.df[mask & (self.df['AwayTeam'] == team)]
            goals_for = matches['FTAG']
            goals_against = matches['FTHG']
            first_half_goals = matches['HTAG']
            first_half_against = matches['HTHG']
        else:
            home = self.df[mask & (self.df['HomeTeam'] == team)].copy()
            away = self.df[mask & (self.df['AwayTeam'] == team)].copy()
            
            home['GF'] = home['FTHG']
            home['GA'] = home['FTAG']
            home['FHG'] = home['HTHG']
            home['FHA'] = home['HTAG']
            
            away['GF'] = away['FTAG']
            away['GA'] = away['FTHG']
            away['FHG'] = away['HTAG']
            away['FHA'] = away['HTHG']
            
            matches = pd.concat([home, away]).sort_values('Date')
            goals_for = matches['GF']
            goals_against = matches['GA']
            first_half_goals = matches['FHG']
            first_half_against = matches['FHA']
        
        matches = matches.tail(last_n)
        goals_for = goals_for.tail(last_n)
        goals_against = goals_against.tail(last_n)
        first_half_goals = first_half_goals.tail(last_n)
        first_half_against = first_half_against.tail(last_n)
        
        if len(matches) < 3:
            return None
        
        total_goals = goals_for + goals_against
        btts = ((goals_for > 0) & (goals_against > 0))
        clean_sheets = (goals_against == 0)
        scored_in = (goals_for > 0)
        
        stats = {
            'games': len(matches),
            'goals_per_game': goals_for.mean(),
            'conceded_per_game': goals_against.mean(),
            'over15_rate': (total_goals > 1.5).mean(),
            'over25_rate': (total_goals > 2.5).mean(),
            'over05_rate': (total_goals > 0.5).mean(),
            'team_over15_rate': (goals_for > 1.5).mean(),
            'team_over05_rate': scored_in.mean(),
            'first_half_goals': first_half_goals.mean(),
            'btts_rate': btts.mean(),
            'clean_sheet_rate': clean_sheets.mean(),
            'scored_in_rate': scored_in.mean(),
            'goals_std': goals_for.std() if len(goals_for) > 1 else 0.5,
        }
        
        return stats
    
    def get_form_momentum(self, team, before_date):
        """Recent 3-match form vs overall 10-match form — measures trend."""
        recent = self.get_team_stats(team, before_date, last_n=3)
        overall = self.get_team_stats(team, before_date, last_n=10)
        if recent is None or overall is None:
            return 0.0
        return recent['goals_per_game'] - overall['goals_per_game']
        
    def calculate_features(self, match_row):
        home_team = match_row['HomeTeam']
        away_team = match_row['AwayTeam']
        match_date = match_row['Date']
        
        home_stats = self.get_team_stats(home_team, match_date, last_n=10)
        away_stats = self.get_team_stats(away_team, match_date, last_n=10)
        home_home_stats = self.get_team_stats(home_team, match_date, last_n=5, home_only=True)
        away_away_stats = self.get_team_stats(away_team, match_date, last_n=5, away_only=True)
        
        if home_stats is None or away_stats is None:
            return None
        
        if home_home_stats is None:
            home_home_stats = home_stats
        if away_away_stats is None:
            away_away_stats = away_stats

        # Get odds if available
        over15_odds = float(match_row.get('P>2.5', 1.5)) if pd.notna(match_row.get('P>2.5')) else 1.5
        under15_odds = float(match_row.get('P<2.5', 2.5)) if pd.notna(match_row.get('P<2.5')) else 2.5

        home_momentum = self.get_form_momentum(home_team, match_date)
        away_momentum = self.get_form_momentum(away_team, match_date)

        # Attack vs defense ratios
        home_attack_strength = home_stats['goals_per_game'] / max(away_stats['conceded_per_game'], 0.3)
        away_attack_strength = away_stats['goals_per_game'] / max(home_stats['conceded_per_game'], 0.3)
        
        features = {
            # Core team stats (original 18)
            'home_goals_per_game': home_stats['goals_per_game'],
            'home_goals_conceded_per_game': home_stats['conceded_per_game'],
            'home_over15_rate': home_stats['over15_rate'],
            'home_over05_rate': home_stats['over05_rate'],
            'home_first_half_goals': home_stats['first_half_goals'],
            'away_goals_per_game': away_stats['goals_per_game'],
            'away_goals_conceded_per_game': away_stats['conceded_per_game'],
            'away_over15_rate': away_stats['over15_rate'],
            'away_over05_rate': away_stats['over05_rate'],
            'away_first_half_goals': away_stats['first_half_goals'],
            'home_home_goals': home_home_stats['goals_per_game'],
            'home_home_conceded': home_home_stats['conceded_per_game'],
            'away_away_goals': away_away_stats['goals_per_game'],
            'away_away_conceded': away_away_stats['conceded_per_game'],
            'total_expected_goals': home_home_stats['goals_per_game'] + away_away_stats['goals_per_game'],
            'defensive_strength': home_home_stats['conceded_per_game'] + away_away_stats['conceded_per_game'],
            'over15_odds': over15_odds,
            'under15_odds': under15_odds,
            # NEW: BTTS and clean sheet
            'home_btts_rate': home_stats['btts_rate'],
            'away_btts_rate': away_stats['btts_rate'],
            'home_clean_sheet_rate': home_stats['clean_sheet_rate'],
            'away_clean_sheet_rate': away_stats['clean_sheet_rate'],
            # NEW: Attack/defense ratios
            'home_attack_strength': home_attack_strength,
            'away_attack_strength': away_attack_strength,
            'attack_vs_defense_ratio': home_attack_strength / max(away_attack_strength, 0.3),
            # NEW: Form momentum
            'home_momentum': home_momentum,
            'away_momentum': away_momentum,
            # NEW: Scoring consistency (lower std = more predictable)
            'home_goals_std': home_stats['goals_std'],
            'away_goals_std': away_stats['goals_std'],
            # NEW: Over 2.5 rates
            'home_over25_rate': home_stats['over25_rate'],
            'away_over25_rate': away_stats['over25_rate'],
            # NEW: Scored-in rate
            'home_scored_in_rate': home_stats['scored_in_rate'],
            'away_scored_in_rate': away_stats['scored_in_rate'],
        }
        
        return features

def prepare_dataset(df):
    calculator = FeatureCalculator(df)
    
    features_list = []
    labels_list = []
    
    print("🔄 Calculating pre-match features...")
    
    for idx, row in df.iterrows():
        if idx % 500 == 0:
            print(f"   {idx}/{len(df)} matches...")
        
        features = calculator.calculate_features(row)
        
        if features is not None:
            features_list.append(features)
            labels_list.append(row)
    
    print(f"✅ {len(features_list)} matches with valid features")
    
    return pd.DataFrame(features_list), labels_list
