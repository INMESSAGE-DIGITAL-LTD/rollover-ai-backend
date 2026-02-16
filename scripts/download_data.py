"""
Download historical match data from Football-Data.co.uk
"""
import requests
import pandas as pd
from pathlib import Path

# Seasons to download (last 3 seasons)
SEASONS = ['2223', '2324', '2425']

# Leagues
LEAGUES = {
    'E0': 'Premier League',
    'SP1': 'La Liga',
    'D1': 'Bundesliga',
    'I1': 'Serie A',
    'F1': 'Ligue 1'
}

def download_data():
    """Download all data"""
    data_dir = Path('../data/raw')
    data_dir.mkdir(parents=True, exist_ok=True)
    
    all_matches = []
    
    for season in SEASONS:
        print(f"\n📅 Downloading {season} season...")
        
        for code, name in LEAGUES.items():
            url = f'https://www.football-data.co.uk/mmz4281/{season}/{code}.csv'
            
            try:
                df = pd.read_csv(url, encoding='latin-1')
                
                # Add metadata
                df['Season'] = season
                df['League'] = name
                
                # Keep only completed matches with scores
                df = df.dropna(subset=['FTHG', 'FTAG', 'HTHG', 'HTAG'])
                
                all_matches.append(df)
                print(f"   ✅ {name}: {len(df)} matches")
                
            except Exception as e:
                print(f"   ⚠️ {name}: {e}")
    
    # Combine all data
    if all_matches:
        combined = pd.concat(all_matches, ignore_index=True)
        
        # Save
        output_file = data_dir / 'all_matches.csv'
        combined.to_csv(output_file, index=False)
        
        print(f"\n✅ Total matches downloaded: {len(combined)}")
        print(f"✅ Saved to: {output_file}")
        
        return combined
    else:
        print("❌ No data downloaded")
        return None

if __name__ == '__main__':
    print("🔄 Downloading historical football data...")
    data = download_data()
    
    if data is not None:
        print(f"\n📊 Data Summary:")
        print(f"   Columns: {', '.join(data.columns[:10])}...")
        print(f"   Date range: {data['Date'].min()} to {data['Date'].max()}")
