# 🚀 Installation Guide - Professional Kraken Trading Bot

## Prerequisites

- Python 3.8 or higher
- Kraken account with API keys
- Webhook endpoint URL

## Quick Installation

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

Or install manually:

```bash
pip install krakenex pandas numpy ta requests python-dotenv
```

### 2. Configure Environment

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` with your settings:

```bash
# Required
KRAKEN_API_KEY=your_actual_api_key
KRAKEN_API_SECRET=your_actual_api_secret
WEBHOOK_URL=https://your-webhook-url.com/signals

# Optional (defaults provided)
LEVERAGE=10
TAKE_PROFIT_PERCENT=5.0
STOP_LOSS_PERCENT=2.0
MIN_CONFIDENCE_SCORE=70
TIMEFRAMES=5,15,60,240,1440
```

### 3. Test Configuration

Test your setup:

```bash
python3 test_connection.py
```

### 4. Run the Bot

```bash
python3 pro_trading_bot.py
```

## Windows Installation

If you're on Windows:

```powershell
# Install dependencies
python -m pip install -r requirements.txt

# Run the bot
python pro_trading_bot.py
```

## Troubleshooting

### ModuleNotFoundError: No module named 'ta'

Install the missing library:

```bash
pip install ta
```

### ModuleNotFoundError: No module named 'krakenex'

Install all dependencies:

```bash
pip install -r requirements.txt
```

### API Connection Error

1. Verify your API keys in `.env`
2. Check API key permissions on Kraken (needs: Query Funds, Query Orders, Create/Modify Orders)
3. Ensure your IP is whitelisted on Kraken (if configured)

### Webhook Connection Error

1. Verify your webhook URL is accessible
2. Test with: `curl -X POST <your-webhook-url> -H "Content-Type: application/json" -d '{"test":true}'`

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| krakenex | >=2.1.0 | Kraken API client |
| pandas | >=1.3.0 | Data manipulation |
| numpy | >=1.21.0 | Numerical computations |
| ta | >=0.10.0 | Technical analysis indicators |
| requests | >=2.26.0 | HTTP requests for webhooks |
| python-dotenv | >=0.19.0 | Environment variables |

## Next Steps

1. ✅ Install dependencies
2. ✅ Configure `.env` file
3. ✅ Test connection
4. ✅ Run the bot
5. 📊 Monitor signals via webhook

For full documentation, see `README_PRO.md`

## Support

- Check logs: `pro_trading_bot.log`
- Review configuration: `config.py`
- Test Kraken API: `test_connection.py`
