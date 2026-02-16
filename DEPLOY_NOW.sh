#!/bin/bash

echo "🚀 Rollover AI Backend - Quick Deploy Script"
echo "=============================================="
echo ""

# Check if GitHub username is provided
if [ -z "$1" ]; then
    echo "❌ Error: Please provide your GitHub username"
    echo ""
    echo "Usage: ./DEPLOY_NOW.sh YOUR_GITHUB_USERNAME"
    echo "Example: ./DEPLOY_NOW.sh sanusimuhammad"
    exit 1
fi

USERNAME=$1
REPO_NAME="rollover-ai-backend"

echo "📋 Deployment Plan:"
echo "   GitHub User: $USERNAME"
echo "   Repo Name: $REPO_NAME"
echo "   Branch: main"
echo ""

# Create GitHub repo using gh CLI
echo "1️⃣ Creating GitHub repository..."
if command -v gh &> /dev/null; then
    gh repo create $REPO_NAME --public --source=. --remote=origin --push
    echo "✅ Repository created and pushed!"
else
    echo "⚠️ GitHub CLI not found. Manual steps:"
    echo ""
    echo "   1. Go to: https://github.com/new"
    echo "   2. Repository name: $REPO_NAME"
    echo "   3. Make it Public"
    echo "   4. Click 'Create repository'"
    echo ""
    echo "   Then run:"
    echo "   git remote add origin https://github.com/$USERNAME/$REPO_NAME.git"
    echo "   git push -u origin main"
    echo ""
fi

echo ""
echo "2️⃣ Next: Deploy to Railway"
echo "   1. Go to: https://railway.app"
echo "   2. Sign in with GitHub"
echo "   3. Click 'New Project'"
echo "   4. Select 'Deploy from GitHub repo'"
echo "   5. Choose: $USERNAME/$REPO_NAME"
echo "   6. Wait 3-5 minutes"
echo "   7. Copy your live URL"
echo ""
echo "3️⃣ Test your API:"
echo "   curl https://YOUR-URL.railway.app/api/predictions/test"
echo ""
echo "✅ Done! Your AI backend will be live in minutes!"
