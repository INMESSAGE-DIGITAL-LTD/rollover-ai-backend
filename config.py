"""
Configuration for multi-market prediction system
"""

# Market definitions
MARKETS = {
    # Full Time Markets
    'ft_over_15': 'Full Time Over 1.5 Goals',
    'ft_under_15': 'Full Time Under 1.5 Goals',
    
    # Team-specific FT Markets
    'home_over_15': 'Home Team Over 1.5 Goals',
    'home_under_15': 'Home Team Under 1.5 Goals',
    'away_over_15': 'Away Team Over 1.5 Goals',
    'away_under_15': 'Away Team Under 1.5 Goals',
    
    # Half Time Markets
    'ht_over_15': 'Half Time Over 1.5 Goals',
    'ht_under_15': 'Half Time Under 1.5 Goals',
    
    # First Half Markets
    'fh_over_05': 'First Half Over 0.5 Goals',
    'fh_under_05': 'First Half Under 0.5 Goals',
    
    # Second Half Markets  
    'sh_over_05': 'Second Half Over 0.5 Goals',
    'sh_under_05': 'Second Half Under 0.5 Goals',
    
    # 0.5 Goals Home/Away
    'home_over_05': 'Home Team Over 0.5 Goals',
    'away_over_05': 'Away Team Over 0.5 Goals',
}

# Confidence thresholds
MIN_CONFIDENCE = 0.65  # 65% minimum to include

# Odds limits
MAX_TOTAL_ODDS = 2.10
MAX_MATCHES = 4

# Feature columns
FEATURE_COLUMNS = [
    # Home team stats
    'home_goals_per_game',
    'home_goals_conceded_per_game',
    'home_win_rate',
    'home_over15_rate',
    'home_over05_rate',
    'home_first_half_goals',
    'home_second_half_goals',
    
    # Away team stats
    'away_goals_per_game',
    'away_goals_conceded_per_game',
    'away_win_rate',
    'away_over15_rate',
    'away_over05_rate',
    'away_first_half_goals',
    'away_second_half_goals',
    
    # Head-to-head
    'h2h_avg_goals',
    'h2h_avg_first_half_goals',
    'h2h_over15_rate',
    
    # League context
    'league_avg_goals',
    'league_over15_rate',
    
    # Odds (from The Odds API)
    'over15_odds',
    'under15_odds',
]

# Data sources
FOOTBALL_DATA_URLS = {
    'epl': 'http://www.football-data.co.uk/mmz4281/{season}/E0.csv',
    'laliga': 'http://www.football-data.co.uk/mmz4281/{season}/SP1.csv',
    'bundesliga': 'http://www.football-data.co.uk/mmz4281/{season}/D1.csv',
    'seriea': 'http://www.football-data.co.uk/mmz4281/{season}/I1.csv',
    'ligue1': 'http://www.football-data.co.uk/mmz4281/{season}/F1.csv',
}

SEASONS = ['2223', '2324', '2425']  # Last 3 seasons
