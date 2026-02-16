# 🚀 Deployment Guide

## ✅ Files Ready for Deployment

All deployment files have been created:
- ✅ `requirements.txt` - Python dependencies
- ✅ `Procfile` - Start command
- ✅ `runtime.txt` - Python version (3.9.18)
- ✅ `railway.json` - Railway config
- ✅ `render.yaml` - Render config
- ✅ `.gitignore` - Ignore large CSV files
- ✅ `app.py` - CORS enabled for Flutter

**Git repository initialized with 29 files committed!**

---

## 📦 Option 1: Deploy to Railway (Recommended)

### Step 1: Create GitHub Repository
```bash
# Create a new repo on GitHub: rollover-ai-backend
# Then push:
cd /Users/sanusi/Desktop/rollover-backend
git remote add origin https://github.com/YOUR_USERNAME/rollover-ai-backend.git
git branch -M main
git push -u origin main
```

### Step 2: Deploy to Railway
1. Go to https://railway.app
2. Sign in with GitHub
3. Click "New Project"
4. Select "Deploy from GitHub repo"
5. Choose `rollover-ai-backend`
6. Railway will auto-detect settings from `railway.json`
7. Wait 3-5 minutes for build
8. Get your live URL: `https://rollover-ai-backend-production.up.railway.app`

**Cost:** $0/month (Free tier: 500 hours/month)

---

## 📦 Option 2: Deploy to Render

### Step 1: Push to GitHub (same as above)

### Step 2: Deploy to Render
1. Go to https://render.com
2. Sign in with GitHub
3. Click "New +" → "Web Service"
4. Connect your `rollover-ai-backend` repo
5. Render auto-detects settings from `render.yaml`
6. Click "Create Web Service"
7. Wait 5-10 minutes for build
8. Get your live URL: `https://rollover-ai-backend.onrender.com`

**Cost:** $0/month (Free tier with sleep after 15 min inactivity)

---

## 📦 Option 3: Deploy to Heroku

### Step 1: Install Heroku CLI
```bash
brew tap heroku/brew && brew install heroku
```

### Step 2: Deploy
```bash
cd /Users/sanusi/Desktop/rollover-backend
heroku login
heroku create rollover-ai-backend
git push heroku main
heroku open
```

**Cost:** $0/month (Free tier: 550 dyno hours/month)

---

## 🧪 Test Deployed API

Once deployed, test with:

```bash
# Replace with your actual URL
curl https://YOUR-APP.railway.app/api/predictions/test

# Should return JSON with predictions
```

---

## 🔗 Connect to Flutter App

Update Flutter app to use live URL:

```dart
// lib/services/prediction_service.dart
class PredictionService {
  static const String baseUrl = 'https://YOUR-APP.railway.app';
  
  Future<Map<String, dynamic>> getPredictions() async {
    final response = await http.get(
      Uri.parse('$baseUrl/api/predictions/test')
    );
    return json.decode(response.body);
  }
}
```

---

## 📊 Deployment Checklist

- ✅ Git repo initialized
- ✅ All files committed (29 files)
- ✅ Trained models included (14 models)
- ✅ Requirements.txt complete
- ✅ CORS enabled for Flutter
- ✅ Gunicorn production server
- ✅ Railway config ready
- ✅ Render config ready
- ⏳ Push to GitHub
- ⏳ Deploy to hosting platform
- ⏳ Test live API
- ⏳ Update Flutter app

---

## 🎯 Recommended: Railway

**Why Railway?**
- ✅ Fastest deployment (3 mins)
- ✅ No sleep on free tier
- ✅ Auto-deploys on git push
- ✅ Better free tier limits
- ✅ Easy environment variables

**Why not Render?**
- ⚠️ Sleeps after 15 min inactivity (slow first request)
- ⚠️ Longer build times

---

## 🔑 Next Steps

1. **Push to GitHub** (see commands above)
2. **Deploy to Railway** (recommended)
3. **Get live URL** from Railway dashboard
4. **Test API:** `curl YOUR_URL/api/predictions/test`
5. **Update Flutter app** with live URL
6. **Done!** 🎉

---

**Need help?** 
- Railway docs: https://docs.railway.app
- Render docs: https://render.com/docs
- Flask deployment: https://flask.palletsprojects.com/en/3.0.x/deploying/

