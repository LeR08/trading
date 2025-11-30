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

    # Trading Parameters
    TRADING_PAIR = os.getenv('TRADING_PAIR', 'XXBTZUSD')
    LEVERAGE = int(os.getenv('LEVERAGE', '3'))
    TAKE_PROFIT_PERCENT = float(os.getenv('TAKE_PROFIT_PERCENT', '3.0'))
    STOP_LOSS_PERCENT = float(os.getenv('STOP_LOSS_PERCENT', '9.0'))

    # Bot Settings
    CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', '60'))  # seconds
    MIN_ORDER_SIZE = float(os.getenv('MIN_ORDER_SIZE', '0.001'))
    MAX_POSITION_SIZE = float(os.getenv('MAX_POSITION_SIZE', '0.1'))

    # Risk Management
    MAX_DAILY_LOSS_PERCENT = float(os.getenv('MAX_DAILY_LOSS_PERCENT', '15.0'))
    MAX_OPEN_POSITIONS = int(os.getenv('MAX_OPEN_POSITIONS', '1'))

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

        if cls.LEVERAGE < 1 or cls.LEVERAGE > 5:
            raise ValueError("Leverage must be between 1 and 5")

        if cls.TAKE_PROFIT_PERCENT <= 0 or cls.STOP_LOSS_PERCENT <= 0:
            raise ValueError("TP and SL must be positive values")

        return True
