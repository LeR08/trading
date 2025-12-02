"""
Unit tests for technical indicators
"""
import unittest
import pandas as pd
import numpy as np
from src.indicators.technical_indicators import TechnicalIndicators


class TestTechnicalIndicators(unittest.TestCase):
    """Test technical indicators"""

    def setUp(self):
        """Set up test data"""
        self.indicators = TechnicalIndicators()

        # Create sample OHLCV data
        np.random.seed(42)
        dates = pd.date_range('2024-01-01', periods=200, freq='3min')

        # Generate synthetic price data
        base_price = 50000
        returns = np.random.randn(200) * 100
        close_prices = base_price + np.cumsum(returns)

        self.df = pd.DataFrame({
            'open': close_prices + np.random.randn(200) * 50,
            'high': close_prices + abs(np.random.randn(200)) * 100,
            'low': close_prices - abs(np.random.randn(200)) * 100,
            'close': close_prices,
            'volume': np.random.rand(200) * 10,
        }, index=dates)

    def test_ema_calculation(self):
        """Test EMA calculation"""
        ema = self.indicators.calculate_ema(self.df['close'], 20)
        self.assertEqual(len(ema), len(self.df))
        self.assertFalse(ema.isna().all())

    def test_rsi_calculation(self):
        """Test RSI calculation"""
        rsi = self.indicators.calculate_rsi(self.df['close'], 14)
        self.assertEqual(len(rsi), len(self.df))

        # RSI should be between 0 and 100
        valid_rsi = rsi.dropna()
        self.assertTrue((valid_rsi >= 0).all())
        self.assertTrue((valid_rsi <= 100).all())

    def test_macd_calculation(self):
        """Test MACD calculation"""
        macd = self.indicators.calculate_macd(self.df['close'])

        self.assertIn('macd', macd)
        self.assertIn('signal', macd)
        self.assertIn('histogram', macd)

        self.assertEqual(len(macd['macd']), len(self.df))

    def test_atr_calculation(self):
        """Test ATR calculation"""
        atr = self.indicators.calculate_atr(self.df, 14)

        self.assertEqual(len(atr), len(self.df))

        # ATR should be positive
        valid_atr = atr.dropna()
        self.assertTrue((valid_atr > 0).all())

    def test_bollinger_bands(self):
        """Test Bollinger Bands"""
        bb = self.indicators.calculate_bollinger_bands(self.df['close'], 20, 2)

        self.assertIn('upper', bb)
        self.assertIn('middle', bb)
        self.assertIn('lower', bb)

        # Upper should be > middle > lower
        valid_idx = ~bb['upper'].isna()
        self.assertTrue((bb['upper'][valid_idx] >= bb['middle'][valid_idx]).all())
        self.assertTrue((bb['middle'][valid_idx] >= bb['lower'][valid_idx]).all())

    def test_rsi_signal(self):
        """Test RSI signal generation"""
        signal = self.indicators.rsi_signal(self.df)

        self.assertIsNotNone(signal)
        self.assertIn(signal.signal, [-1, -0.5, 0, 0.5, 1])
        self.assertTrue(0 <= signal.value <= 100)

    def test_all_indicators(self):
        """Test calculating all indicators"""
        signals = self.indicators.calculate_all_indicators(self.df)

        # Should have 12 indicators
        expected_indicators = [
            'ema_8', 'ema_21', 'sma_50', 'rsi_14', 'macd',
            'atr_14', 'bollinger', 'stochastic', 'adx_14',
            'cci_20', 'obv', 'vwap'
        ]

        for indicator in expected_indicators:
            self.assertIn(indicator, signals, f"Missing indicator: {indicator}")

        # All signals should be in valid range
        for name, signal in signals.items():
            self.assertTrue(-1 <= signal.signal <= 1, f"{name} signal out of range: {signal.signal}")
            self.assertTrue(0 <= signal.strength <= 1, f"{name} strength out of range: {signal.strength}")


if __name__ == '__main__':
    unittest.main()
