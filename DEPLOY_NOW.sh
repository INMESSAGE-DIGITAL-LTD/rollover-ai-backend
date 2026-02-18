#!/bin/bash

echo "🚀 Rollover AI Backend - Deploy to Render"
echo "==========================================="
echo ""

echo "1️⃣ Pushing to GitHub..."
cd /Users/sanusi/Desktop/rollover-backend
git add -A && git commit -m "deploy" && git push origin main

echo ""
echo "2️⃣ Render auto-deploys from GitHub."
echo "   Dashboard: https://dashboard.render.com"
echo "   Live URL:  https://rollover-ai-backend.onrender.com"
echo ""
echo "3️⃣ Test your API:"
echo "   curl https://rollover-ai-backend.onrender.com/api/today"
echo ""
echo "✅ Done!"
