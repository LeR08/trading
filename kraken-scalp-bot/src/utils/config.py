"""
Configuration loader
"""
import os
from pathlib import Path
from typing import Dict, Any
import yaml
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)


class Config:
    """Configuration management"""

    def __init__(self, config_path: str = "config/config.yaml"):
        """
        Load configuration from YAML and environment

        Args:
            config_path: Path to config.yaml
        """
        # Load .env file
        env_path = Path(".env")
        if env_path.exists():
            load_dotenv(env_path)
            logger.info("Loaded .env file")
        else:
            logger.warning(".env file not found")

        # Load YAML config
        config_full_path = Path(config_path)
        if not config_full_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(config_full_path, 'r') as f:
            self._config = yaml.safe_load(f)

        logger.info(f"Loaded configuration from {config_path}")

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation

        Args:
            key: Configuration key (e.g., 'trading.pair')
            default: Default value if key not found

        Returns:
            Configuration value
        """
        keys = key.split('.')
        value = self._config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def get_env(self, key: str, default: str = None) -> str:
        """
        Get environment variable

        Args:
            key: Environment variable name
            default: Default value

        Returns:
            Environment variable value
        """
        return os.getenv(key, default)

    @property
    def kraken_api_key(self) -> str:
        """Get Kraken API key from environment"""
        return self.get_env("KRK_KEY", "")

    @property
    def kraken_api_secret(self) -> str:
        """Get Kraken API secret from environment"""
        return self.get_env("KRK_SECRET", "")

    @property
    def trading_pair(self) -> str:
        """Get trading pair"""
        return self.get("trading.pair", "XBTUSD")

    @property
    def leverage(self) -> int:
        """Get leverage"""
        return self.get("trading.leverage", 3)

    @property
    def timeframes(self) -> list:
        """Get timeframes"""
        return self.get("trading.timeframes", [3, 15])

    @property
    def refresh_interval(self) -> int:
        """Get refresh interval in seconds"""
        return self.get("trading.refresh_interval", 40)

    @property
    def confidence_threshold(self) -> float:
        """Get confidence threshold"""
        return self.get("signal.confidence_threshold", 0.66)

    @property
    def indicator_weights(self) -> Dict[str, float]:
        """Get indicator weights"""
        return self.get("signal.weights", {})

    @property
    def risk_per_trade(self) -> float:
        """Get risk per trade"""
        return self.get("risk.risk_per_trade", 0.01)

    @property
    def execution_mode(self) -> str:
        """Get execution mode"""
        return self.get("trading.mode", "paper")

    def validate(self) -> bool:
        """
        Validate configuration

        Returns:
            True if valid
        """
        errors = []

        # Check API keys if not in paper mode
        if self.execution_mode != "paper":
            if not self.kraken_api_key:
                errors.append("KRK_KEY not set in environment")
            if not self.kraken_api_secret:
                errors.append("KRK_SECRET not set in environment")

        # Validate weights sum to 1.0
        weights = self.indicator_weights
        if weights:
            total = sum(weights.values())
            if abs(total - 1.0) > 0.01:
                errors.append(f"Indicator weights sum to {total}, should be 1.0")

        if errors:
            for error in errors:
                logger.error(f"Config validation error: {error}")
            return False

        logger.info("Configuration validated successfully")
        return True
