"""
Calculate pre-match features from historical data
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

class FeatureCalculator:
    def __init__(self, df):
        """
        Initialize with full dataset
        """
        self.df = df.copy()
        self.df['Date'] = pd.to_datetime(self.df['Date'], format='%d/%m/%Y', errors='coerce')
        self.df = self.df.sort_values('Date')
        
    def get_team_stats(self, team, before_date, last_n=10, home_only=False, away_only=False):
        """
        Get team stats from last N matches before a date
        """
        # Filter matches before this date
        mask = self.df['Date'] < before_date
        
        # Get matches with this team
        if home_only:
            matches = self.df[mask & (self.df['HomeTeam'] == team)]
            goals_for = matches['FTHG']
            goals_against = matches['FTAG']
            first_half_goals = matches['HTHG']
        elif away_only:
            matches = self.df[mask & (self.df['AwayTeam'] == team)]
            goals_for = matches['FTAG']
            goals_against = matches['FTHG']
            first_half_goals = matches['HTAG']
        else:
            home = self.df[mask & (self.df['HomeTeam'] == team)].copy()
            away = self.df[mask & (self.df['AwayTeam'] == team)].copy()
            
            home['GF'] = home['FTHG']
            home['GA'] = home['FTAG']
            home['FHG'] = home['HTHG']
            
            away['GF'] = away['FTAG']
            away['GA'] = away['FTHG']
            away['FHG'] = away['HTAG']
            
            matches = pd.concat([home, away]).sort_values('Date')
            goals_for = matches['GF']
            goals_against = matches['GA']
            first_half_goals = matches['FHG']
        
        # Take last N
        matches = matches.tail(last_n)
        goals_for = goals_for.tail(last_n)
        goals_against = goals_against.tail(last_n)
        first_half_goals = first_half_goals.tail(last_n)
        
        if len(matches) == 0:
            return None
        
        # Calculate stats
        stats = {
            'games': len(matches),
            'goals_per_game': goals_for.mean(),
            'conceded_per_game': goals_against.mean(),
            'over15_rate': ((goals_for + goals_against) > 1.5).mean(),
            'over05_rate': ((goals_for + goals_against) > 0.5).mean(),
            'team_over15_rate': (goals_for > 1.5).mean(),
            'team_over05_rate': (goals_for > 0.5).mean(),
            'first_half_goals': first_half_goals.mean(),
        }
        
        return stats
    
    def calculate_features(self, match_row):
        """
        Calculate all features for a single match
        """
        home_team = match_row['HomeTeam']
        away_team = match_row['AwayTeam']
        match_date = match_row['Date']
        
        # Get team form (last 10 matches)
        home_stats = self.get_team_stats(home_team, match_date, last_n=10)
        away_stats = self.get_team_stats(away_team, match_date, last_n=10)
        
        # Home/Away specific
        home_home_stats = self.get_team_stats(home_team, match_date, last_n=5, home_only=True)
        away_away_stats = self.get_team_stats(away_team, match_date, last_n=5, away_only=True)
        
        # If no history, use defaults
        if home_stats is None or away_stats is None:
            return None
        
        if home_home_stats is None:
            home_home_stats = home_stats
        if away_away_stats is None:
            away_away_stats = away_stats
        
        # Build feature dict
        features = {
            # Home team overall
            'home_goals_per_game': home_stats['goals_per_game'],
            'home_goals_conceded_per_game': home_stats['conceded_per_game'],
            'home_over15_rate': home_stats['over15_rate'],
            'home_over05_rate': home_stats['over05_rate'],
            'home_first_half_goals': home_stats['first_half_goals'],
            
            # Away team overall
            'away_goals_per_game': away_stats['goals_per_game'],
            'away_goals_conceded_per_game': away_stats['conceded_per_game'],
            'away_over15_rate': away_stats['over15_rate'],
            'away_over05_rate': away_stats['over05_rate'],
            'away_first_half_goals': away_stats['first_half_goals'],
            
            # Home advantage
            'home_home_goals': home_home_stats['goals_per_game'],
            'home_home_conceded': home_home_stats['conceded_per_game'],
            
            # Away disadvantage
            'away_away_goals': away_away_stats['goals_per_game'],
            'away_away_conceded': away_away_stats['conceded_per_game'],
            
            # Combined stats
            'total_expected_goals': home_home_stats['goals_per_game'] + away_away_stats['goals_per_game'],
            'defensive_strength': home_home_stats['conceded_per_game'] + away_away_stats['conceded_per_game'],
            
            # Placeholders (would need odds data)
            'over15_odds': 1.5,
            'under15_odds': 2.5,
        }
        
        return features

def prepare_dataset(df):
    """
    Prepare full dataset with features
    """
    calculator = FeatureCalculator(df)
    
    features_list = []
    labels_list = []
    
    print("🔄 Calculating pre-match features...")
    
    for idx, row in df.iterrows():
        if idx % 500 == 0:
            print(f"   {idx}/{len(df)} matches...")
        
        # Calculate features
        features = calculator.calculate_features(row)
        
        if features is not None:
            features_list.append(features)
            labels_list.append(row)
    
    print(f"✅ {len(features_list)} matches with valid features")
    
    return pd.DataFrame(features_list), labels_list
