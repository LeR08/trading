"""
Configuration module for Kraken Trading Bot
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Trading bot configuration"""

    # Kraken API
    KRAKEN_API_KEY = os.getenv('KRAKEN_API_KEY', '')
    KRAKEN_API_SECRET = os.getenv('KRAKEN_API_SECRET', '')

    # Webhook Configuration
    WEBHOOK_URL = os.getenv('WEBHOOK_URL', '')

    # Trading Parameters
    TRADING_PAIR = os.getenv('TRADING_PAIR', 'XXBTZUSD')
    LEVERAGE = int(os.getenv('LEVERAGE', '10'))
    TAKE_PROFIT_PERCENT = float(os.getenv('TAKE_PROFIT_PERCENT', '5.0'))
    STOP_LOSS_PERCENT = float(os.getenv('STOP_LOSS_PERCENT', '2.0'))

    # Bot Settings
    PAPER_TRADING = os.getenv('PAPER_TRADING', 'true').lower() == 'true'
    CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', '60'))  # seconds
    MIN_ORDER_SIZE = float(os.getenv('MIN_ORDER_SIZE', '0.001'))
    MAX_POSITION_SIZE = float(os.getenv('MAX_POSITION_SIZE', '0.1'))

    # Risk Management
    MAX_DAILY_LOSS_PERCENT = float(os.getenv('MAX_DAILY_LOSS_PERCENT', '10.0'))
    MAX_OPEN_POSITIONS = int(os.getenv('MAX_OPEN_POSITIONS', '3'))
    MIN_CONFIDENCE_SCORE = int(os.getenv('MIN_CONFIDENCE_SCORE', '70'))

    # Multi-Timeframe Analysis
    TIMEFRAMES = [int(tf.strip()) for tf in os.getenv('TIMEFRAMES', '5,15,60,240,1440').split(',')]

    # Timeframe weights for confidence score calculation
    _weights_str = os.getenv('TIMEFRAME_WEIGHTS', '1:1,5:2,15:3,30:4,60:5,240:6,1440:7,10080:5,21600:3')
    TIMEFRAME_WEIGHTS = {}
    for weight_pair in _weights_str.split(','):
        tf, weight = weight_pair.split(':')
        TIMEFRAME_WEIGHTS[int(tf)] = int(weight)

    # Technical Indicators Settings
    RSI_PERIOD = 14
    RSI_OVERBOUGHT = 70
    RSI_OVERSOLD = 30

    MACD_FAST = 12
    MACD_SLOW = 26
    MACD_SIGNAL = 9

    BOLLINGER_PERIOD = 20
    BOLLINGER_STD = 2

    EMA_SHORT = 9
    EMA_MEDIUM = 21
    EMA_LONG = 50

    VOLUME_MA_PERIOD = 20

    @classmethod
    def validate(cls):
        """Validate configuration"""
        if not cls.KRAKEN_API_KEY or not cls.KRAKEN_API_SECRET:
            raise ValueError("API credentials not set. Please configure .env file")

        if not cls.WEBHOOK_URL:
            raise ValueError("WEBHOOK_URL not set. Please configure .env file")

        if cls.LEVERAGE < 1 or cls.LEVERAGE > 10:
            raise ValueError("Leverage must be between 1 and 10")

        if cls.TAKE_PROFIT_PERCENT <= 0 or cls.STOP_LOSS_PERCENT <= 0:
            raise ValueError("TP and SL must be positive values")

        if cls.MIN_CONFIDENCE_SCORE < 0 or cls.MIN_CONFIDENCE_SCORE > 100:
            raise ValueError("MIN_CONFIDENCE_SCORE must be between 0 and 100")

        return True
