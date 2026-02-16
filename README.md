# Rollover AI Multi-Market Prediction Backend

## 🎯 What This AI Predicts

**14 Different Markets:**

### Full Time Markets
1. ✅ **FT Over 1.5** - Match will have 2+ total goals
2. ❌ **FT Under 1.5** - Match will have 0-1 goals

### Team-Specific Markets
3. ✅ **Home Over 1.5** - Home team scores 2+ goals
4. ❌ **Home Under 1.5** - Home team scores 0-1 goals
5. ✅ **Away Over 1.5** - Away team scores 2+ goals
6. ❌ **Away Under 1.5** - Away team scores 0-1 goals

### Half Time Markets
7. ✅ **HT Over 1.5** - 2+ goals by half time
8. ❌ **HT Under 1.5** - 0-1 goals by half time

### First/Second Half Markets
9. ✅ **FH Over 0.5** - At least 1 goal in first half
10. ❌ **FH Under 0.5** - No goals in first half
11. ✅ **SH Over 0.5** - At least 1 goal in second half
12. ❌ **SH Under 0.5** - No goals in second half

### 0.5 Goals Markets
13. ✅ **Home Over 0.5** - Home team scores at least 1
14. ✅ **Away Over 0.5** - Away team scores at least 1

---

## 📁 Project Structure

```
rollover-backend/
├── app.py                      # Flask API server
├── config.py                   # Configuration & market definitions
├── requirements.txt            # Python dependencies
├── models/
│   ├── multi_market_predictor.py   # 14 XGBoost models
│   └── trained/                    # Saved models (after training)
├── utils/
│   └── label_generator.py      # Generate labels from historical data
├── data/
│   └── sample_matches.csv      # Training data
└── scripts/
    └── train.py                # Training script (TODO)
```

---

## 🚀 Quick Start

### 1. Install Dependencies
```bash
cd /Users/sanusi/Desktop/rollover-backend
pip3 install -r requirements.txt
```

### 2. Download Historical Data
```bash
# Download last 3 seasons for top leagues
# Using Football-Data.co.uk (FREE)
curl -o data/epl_2324.csv http://www.football-data.co.uk/mmz4281/2324/E0.csv
curl -o data/laliga_2324.csv http://www.football-data.co.uk/mmz4281/2324/SP1.csv
# ... more leagues
```

### 3. Train Models
```bash
python3 scripts/train.py
# This will:
# - Load historical data
# - Generate labels for all 14 markets
# - Train 14 XGBoost models
# - Save models to models/trained/
```

### 4. Start API
```bash
python3 app.py
# API runs on http://localhost:5000
```

### 5. Test API
```bash
# Get all markets
curl http://localhost:5000/api/markets

# Get daily predictions
curl http://localhost:5000/api/predictions/daily

# Get optimized slip
curl http://localhost:5000/api/predictions/slip
```

---

## 🔌 API Endpoints

### `GET /`
Health check

### `GET /api/markets`
List all 14 markets

### `GET /api/predictions/daily`
Get predictions for all matches today

**Response:**
```json
{
  "date": "2026-02-16",
  "total_matches": 10,
  "predictions": [
    {
      "match": "Man City vs Arsenal",
      "home_team": "Man City",
      "away_team": "Arsenal",
      "league": "Premier League",
      "kickoff": "2026-02-16T15:00:00Z",
      "markets": {
        "ft_over_15": {
          "prediction": "YES",
          "confidence": 0.85,
          "odds": 1.30
        },
        "home_over_15": {
          "prediction": "YES",
          "confidence": 0.72,
          "odds": 1.65
        }
        // ... all 14 markets
      }
    }
  ]
}
```

### `GET /api/predictions/slip`
Get optimized accumulator (1-4 matches, total odds ≤ 2.10)

**Response:**
```json
{
  "date": "2026-02-16",
  "matches": [
    {
      "match": "Man City vs Arsenal",
      "market": "FT Over 1.5",
      "confidence": 0.85,
      "odds": 1.30
    },
    {
      "match": "Bayern vs Dortmund",
      "market": "Home Over 0.5",
      "confidence": 0.90,
      "odds": 1.15
    }
  ],
  "total_odds": 1.50,
  "combined_confidence": 0.77,
  "expected_value": 1.15
}
```

### `POST /api/predict`
Predict all markets for a single match

**Request:**
```json
{
  "home_team": "Barcelona",
  "away_team": "Real Madrid",
  "home_gpg": 2.5,
  "away_gpg": 2.0
}
```

**Response:**
```json
{
  "match": "Barcelona vs Real Madrid",
  "predictions": {
    "ft_over_15": 0.89,
    "home_over_15": 0.75,
    "fh_over_05": 0.85,
    // ... all 14 markets
  }
}
```

---

## 📊 How the AI Learns

### Training Data Format
```csv
Date,HomeTeam,AwayTeam,FTHG,FTAG,HTHG,HTAG
18/08/2023,Man City,Arsenal,3,1,2,0
```

### Label Generation
For each historical match, we create 14 binary labels:

**Example: Man City 3-1 Arsenal (HT: 2-0)**
- `ft_over_15` = 1 ✅ (4 total goals > 1.5)
- `ft_under_15` = 0 ❌
- `home_over_15` = 1 ✅ (Man City scored 3 > 1.5)
- `home_under_15` = 0 ❌
- ... etc

### Model Architecture
- **14 XGBoost models** (one per market)
- Each trained on 10,000+ historical matches
- Features: team form, goals, head-to-head, odds
- Target accuracy: 70-75% per market

---

## 🎓 Next Steps

### ✅ Completed
- ✅ Project structure created
- ✅ Label generator built
- ✅ Multi-market predictor ready
- ✅ Flask API skeleton

### 📋 TODO
1. **Create training script** (`scripts/train.py`)
2. **Download full historical data** (3-5 seasons)
3. **Feature engineering** (calculate team stats)
4. **Train all 14 models**
5. **Integrate with The Odds API** (fetch today's matches)
6. **Build slip optimization algorithm**
7. **Deploy to Railway/Render**
8. **Connect to Flutter app**

---

## 💰 Cost Breakdown

- Historical Data: **FREE** (Football-Data.co.uk)
- Training: **FREE** (local computer)
- The Odds API: **FREE** (500 requests/month)
- Hosting: **FREE** (Railway/Render free tier)

**Total: $0/month** ✅

---

## 📞 Integration with Flutter

```dart
// In your Flutter app
class PredictionService {
  final String apiUrl = 'https://your-backend.com/api';
  
  Future<DailySlip> getDailySlip() async {
    final response = await http.get('$apiUrl/predictions/slip');
    return DailySlip.fromJson(json.decode(response.body));
  }
}
```

---

Ready to train the models! 🚀
# v2.1 - Mixed Markets
