# 🚀 Deployment Guide — Render

## ✅ Files Ready

- ✅ `requirements.txt` — Python dependencies
- ✅ `Procfile` — Start command
- ✅ `runtime.txt` — Python version
- ✅ `render.yaml` — Render config
- ✅ `.gitignore` — Ignore large CSV files
- ✅ `app.py` — CORS enabled for Flutter

---

## 📦 Deploy to Render

### Step 1: Push to GitHub
```bash
cd /Users/sanusi/Desktop/rollover-backend
git push -u origin main
```

### Step 2: Deploy on Render
1. Go to https://render.com
2. Sign in with GitHub
3. Click "New +" → "Web Service"
4. Connect your `rollover-ai-backend` repo
5. Render auto-detects settings from `render.yaml`
6. Click "Create Web Service"
7. Wait 5-10 minutes for build
8. Live URL: `https://rollover-ai-backend.onrender.com`

---

## 🧪 Test Deployed API

```bash
curl https://rollover-ai-backend.onrender.com/
curl https://rollover-ai-backend.onrender.com/api/today
```

---

## 🔗 Connect to Flutter App

The Flutter app is already configured to use:
```
https://rollover-ai-backend.onrender.com
```

---

## 📊 Deployment Checklist

- ✅ Git repo initialized
- ✅ Trained models included (24 models)
- ✅ Requirements.txt complete
- ✅ CORS enabled for Flutter
- ✅ Gunicorn production server
- ✅ Render config ready
- ✅ Auto-deploys on git push

