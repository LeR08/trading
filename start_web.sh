#!/bin/bash

# Kraken Trading Bot - Web Interface Start Script

echo "🚀 Kraken Trading Bot - Web Interface"
echo "======================================"
echo ""

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

echo ""
echo "✅ Starting web interface..."
echo "🌐 Dashboard will be available at: http://localhost:5000"
echo "⚙️  Settings page: http://localhost:5000/settings"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Run the web app
python web_app.py
