"""
Lightweight team stats calculator using only csv + numpy (no pandas)
Loads historical data and computes rolling team statistics for predictions
"""
import csv
import numpy as np
from collections import defaultdict
from datetime import datetime


class TeamStatsCalculator:
    def __init__(self, csv_path='data/raw/all_matches.csv'):
        self.matches = []
        self.team_matches = defaultdict(list)
        self._load_csv(csv_path)

    def _load_csv(self, path):
        try:
            with open(path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        match = {
                            'home': row.get('HomeTeam', ''),
                            'away': row.get('AwayTeam', ''),
                            'fthg': int(float(row.get('FTHG', 0) or 0)),
                            'ftag': int(float(row.get('FTAG', 0) or 0)),
                            'hthg': int(float(row.get('HTHG', 0) or 0)),
                            'htag': int(float(row.get('HTAG', 0) or 0)),
                            'date': row.get('Date', ''),
                            'league': row.get('League', row.get('Div', '')),
                        }
                        self.matches.append(match)
                        self.team_matches[match['home']].append(match)
                        self.team_matches[match['away']].append(match)
                    except (ValueError, TypeError):
                        continue
            print(f"✅ Loaded {len(self.matches)} matches, {len(self.team_matches)} teams")
        except FileNotFoundError:
            print(f"⚠️ No historical data at {path}")

    def get_team_stats(self, team_name, last_n=10):
        """Get rolling stats for a team from last N matches"""
        # Find best matching team name
        team = self._find_team(team_name)
        if not team:
            return self._default_stats()

        matches = self.team_matches[team][-last_n:]
        if not matches:
            return self._default_stats()

        goals_for = []
        goals_against = []
        fh_goals = []
        total_goals = []

        for m in matches:
            if m['home'] == team:
                goals_for.append(m['fthg'])
                goals_against.append(m['ftag'])
                fh_goals.append(m['hthg'])
            else:
                goals_for.append(m['ftag'])
                goals_against.append(m['fthg'])
                fh_goals.append(m['htag'])
            total_goals.append(m['fthg'] + m['ftag'])

        gf = np.array(goals_for, dtype=float)
        ga = np.array(goals_against, dtype=float)
        fh = np.array(fh_goals, dtype=float)
        tg = np.array(total_goals, dtype=float)

        return {
            'goals_per_game': float(np.mean(gf)),
            'conceded_per_game': float(np.mean(ga)),
            'over15_rate': float(np.mean(tg > 1.5)),
            'over05_rate': float(np.mean(tg > 0.5)),
            'first_half_goals': float(np.mean(fh)),
            'games': len(matches),
        }

    def get_home_stats(self, team_name, last_n=5):
        """Get stats when playing at home"""
        team = self._find_team(team_name)
        if not team:
            return self._default_stats()

        home_matches = [m for m in self.team_matches[team] if m['home'] == team][-last_n:]
        if not home_matches:
            return self._default_stats()

        gf = np.array([m['fthg'] for m in home_matches], dtype=float)
        ga = np.array([m['ftag'] for m in home_matches], dtype=float)

        return {
            'goals_per_game': float(np.mean(gf)),
            'conceded_per_game': float(np.mean(ga)),
        }

    def get_away_stats(self, team_name, last_n=5):
        """Get stats when playing away"""
        team = self._find_team(team_name)
        if not team:
            return self._default_stats()

        away_matches = [m for m in self.team_matches[team] if m['away'] == team][-last_n:]
        if not away_matches:
            return self._default_stats()

        gf = np.array([m['ftag'] for m in away_matches], dtype=float)
        ga = np.array([m['fthg'] for m in away_matches], dtype=float)

        return {
            'goals_per_game': float(np.mean(gf)),
            'conceded_per_game': float(np.mean(ga)),
        }

    def build_match_features(self, home_team, away_team, over15_odds=1.5, under15_odds=2.5):
        """Build the 18-feature dict needed by the AI model"""
        home = self.get_team_stats(home_team)
        away = self.get_team_stats(away_team)
        home_h = self.get_home_stats(home_team)
        away_a = self.get_away_stats(away_team)

        return {
            'home_goals_per_game': home['goals_per_game'],
            'home_goals_conceded_per_game': home['conceded_per_game'],
            'home_over15_rate': home['over15_rate'],
            'home_over05_rate': home['over05_rate'],
            'home_first_half_goals': home['first_half_goals'],
            'away_goals_per_game': away['goals_per_game'],
            'away_goals_conceded_per_game': away['conceded_per_game'],
            'away_over15_rate': away['over15_rate'],
            'away_over05_rate': away['over05_rate'],
            'away_first_half_goals': away['first_half_goals'],
            'home_home_goals': home_h['goals_per_game'],
            'home_home_conceded': home_h['conceded_per_game'],
            'away_away_goals': away_a['goals_per_game'],
            'away_away_conceded': away_a['conceded_per_game'],
            'total_expected_goals': home_h['goals_per_game'] + away_a['goals_per_game'],
            'defensive_strength': home_h['conceded_per_game'] + away_a['conceded_per_game'],
            'over15_odds': over15_odds,
            'under15_odds': under15_odds,
        }

    def _find_team(self, name):
        """Fuzzy match team name to our database"""
        if not name:
            return None
        # Exact match
        if name in self.team_matches:
            return name
        # Case-insensitive
        lower = name.lower()
        for team in self.team_matches:
            if team.lower() == lower:
                return team
        # Partial match
        for team in self.team_matches:
            if lower in team.lower() or team.lower() in lower:
                return team
        # Common name mappings
        mappings = {
            'man city': 'Man City', 'manchester city': 'Man City',
            'man united': 'Man United', 'manchester united': 'Man United',
            'man utd': 'Man United',
            'tottenham': 'Tottenham', 'spurs': 'Tottenham',
            'newcastle': 'Newcastle', 'newcastle united': 'Newcastle',
            'wolves': 'Wolverhampton', 'wolverhampton': 'Wolverhampton',
            'west ham': 'West Ham', 'west ham united': 'West Ham',
            'nottingham': "Nott'm Forest", "nottingham forest": "Nott'm Forest",
            'atletico madrid': 'Ath Madrid', 'atletico': 'Ath Madrid',
            'athletic bilbao': 'Ath Bilbao',
            'real madrid': 'Real Madrid', 'barcelona': 'Barcelona',
            'bayern munich': 'Bayern Munich', 'bayern': 'Bayern Munich',
            'borussia dortmund': 'Dortmund', 'dortmund': 'Dortmund',
            'rb leipzig': 'RB Leipzig', 'leipzig': 'RB Leipzig',
            'inter milan': 'Inter', 'inter': 'Inter',
            'ac milan': 'Milan', 'milan': 'Milan',
            'juventus': 'Juventus',
            'napoli': 'Napoli',
            'paris saint germain': 'Paris SG', 'psg': 'Paris SG',
            'lyon': 'Lyon', 'marseille': 'Marseille',
        }
        lower_name = name.lower().strip()
        if lower_name in mappings:
            mapped = mappings[lower_name]
            if mapped in self.team_matches:
                return mapped
        return None

    def _default_stats(self):
        return {
            'goals_per_game': 1.3,
            'conceded_per_game': 1.2,
            'over15_rate': 0.55,
            'over05_rate': 0.78,
            'first_half_goals': 0.6,
            'games': 0,
        }

    def get_all_teams(self):
        """Return list of all known teams"""
        return sorted(self.team_matches.keys())
