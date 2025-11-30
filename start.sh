#!/bin/bash

# Kraken Trading Bot - Quick Start Script

echo "🚀 Kraken Professional Trading Bot - Quick Start"
echo "================================================"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found!"
    echo "📝 Please copy .env.example to .env and configure your API keys:"
    echo "   cp .env.example .env"
    echo "   nano .env"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install/update dependencies
echo "📥 Installing dependencies..."
pip install -q -r requirements.txt

# Check if API keys are configured
if grep -q "your_api_key_here" .env || grep -q "your_api_secret_here" .env; then
    echo ""
    echo "⚠️  WARNING: API keys not configured!"
    echo "📝 Please edit .env file and add your Kraken API credentials:"
    echo "   nano .env"
    echo ""
    read -p "Press Enter to continue anyway (bot will fail) or Ctrl+C to exit..."
fi

echo ""
echo "✅ Starting trading bot..."
echo ""

# Run the bot
python bot.py
