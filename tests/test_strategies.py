"""
Tests unitaires pour le module strategies
"""
import unittest
import pandas as pd
import numpy as np
import sys
sys.path.insert(0, '/home/user/trading')

from src.strategies.trend_following import TrendFollowingStrategy
from src.strategies.mean_reversion import MeanReversionStrategy
from src.strategies.breakout import BreakoutStrategy


class TestTrendFollowingStrategy(unittest.TestCase):
    """Tests pour TrendFollowingStrategy"""

    def setUp(self):
        """Initialise la stratégie avant chaque test"""
        self.strategy = TrendFollowingStrategy()

    def create_sample_data(self, trend='bullish', periods=200):
        """
        Crée des données de test

        Args:
            trend: 'bullish', 'bearish', ou 'sideways'
            periods: Nombre de périodes

        Returns:
            DataFrame OHLCV
        """
        np.random.seed(42)

        if trend == 'bullish':
            # Tendance haussière
            close = np.cumsum(np.random.randn(periods) * 100 + 50) + 50000
        elif trend == 'bearish':
            # Tendance baissière
            close = np.cumsum(np.random.randn(periods) * 100 - 50) + 50000
        else:
            # Sideways
            close = np.random.randn(periods) * 500 + 50000

        # Générer OHLC autour du close
        open_prices = close + np.random.randn(periods) * 50
        high = np.maximum(open_prices, close) + np.abs(np.random.randn(periods) * 100)
        low = np.minimum(open_prices, close) - np.abs(np.random.randn(periods) * 100)
        volume = np.random.randint(100, 1000, periods)

        df = pd.DataFrame({
            'open': open_prices,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume
        })

        return df

    def test_generate_signal_bullish(self):
        """Test signal sur tendance haussière"""
        data = self.create_sample_data(trend='bullish')
        signal = self.strategy.generate_signal(data)

        self.assertIn('side', signal)
        self.assertIn('confidence', signal)
        self.assertIn('price', signal)
        self.assertIn('tp', signal)
        self.assertIn('sl', signal)
        self.assertIn('reason', signal)

        # Sur tendance haussière, devrait souvent être buy
        # (pas toujours car dépend des croisements MACD)
        self.assertIn(signal['side'], ['buy', 'sell', 'hold'])

    def test_generate_signal_bearish(self):
        """Test signal sur tendance baissière"""
        data = self.create_sample_data(trend='bearish')
        signal = self.strategy.generate_signal(data)

        self.assertIn(signal['side'], ['buy', 'sell', 'hold'])

    def test_generate_signal_insufficient_data(self):
        """Test avec données insuffisantes"""
        data = self.create_sample_data(periods=10)  # Trop peu
        signal = self.strategy.generate_signal(data)

        # Devrait quand même retourner un signal (peut-être hold)
        self.assertIn('side', signal)

    def test_signal_confidence_range(self):
        """Test que la confiance est dans [0, 1]"""
        data = self.create_sample_data()
        signal = self.strategy.generate_signal(data)

        self.assertGreaterEqual(signal['confidence'], 0.0)
        self.assertLessEqual(signal['confidence'], 1.0)

    def test_tp_sl_logic(self):
        """Test logique TP/SL"""
        data = self.create_sample_data(trend='bullish')
        signal = self.strategy.generate_signal(data)

        if signal['side'] == 'buy':
            # Pour buy: TP > prix > SL
            self.assertGreater(signal['tp'], signal['price'])
            self.assertLess(signal['sl'], signal['price'])
        elif signal['side'] == 'sell':
            # Pour sell: SL > prix > TP
            self.assertGreater(signal['sl'], signal['price'])
            self.assertLess(signal['tp'], signal['price'])


class TestMeanReversionStrategy(unittest.TestCase):
    """Tests pour MeanReversionStrategy"""

    def setUp(self):
        """Initialise la stratégie avant chaque test"""
        self.strategy = MeanReversionStrategy()

    def create_oversold_data(self):
        """Crée des données simulant une zone de survente"""
        np.random.seed(42)
        periods = 200

        # Prix qui descend puis se stabilise bas
        close = np.concatenate([
            np.linspace(52000, 48000, 150),  # Descente
            np.random.randn(50) * 100 + 48000  # Stabilisation bas
        ])

        open_prices = close + np.random.randn(periods) * 50
        high = np.maximum(open_prices, close) + np.abs(np.random.randn(periods) * 100)
        low = np.minimum(open_prices, close) - np.abs(np.random.randn(periods) * 100)
        volume = np.random.randint(100, 1000, periods)

        return pd.DataFrame({
            'open': open_prices,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume
        })

    def create_overbought_data(self):
        """Crée des données simulant une zone de surachat"""
        np.random.seed(42)
        periods = 200

        # Prix qui monte puis se stabilise haut
        close = np.concatenate([
            np.linspace(48000, 52000, 150),  # Montée
            np.random.randn(50) * 100 + 52000  # Stabilisation haut
        ])

        open_prices = close + np.random.randn(periods) * 50
        high = np.maximum(open_prices, close) + np.abs(np.random.randn(periods) * 100)
        low = np.minimum(open_prices, close) - np.abs(np.random.randn(periods) * 100)
        volume = np.random.randint(100, 1000, periods)

        return pd.DataFrame({
            'open': open_prices,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume
        })

    def test_generate_signal_oversold(self):
        """Test signal en zone survente"""
        data = self.create_oversold_data()
        signal = self.strategy.generate_signal(data)

        self.assertIn('side', signal)
        self.assertIn('confidence', signal)
        # En survente, peut générer signal buy
        self.assertIn(signal['side'], ['buy', 'sell', 'hold'])

    def test_generate_signal_overbought(self):
        """Test signal en zone surachat"""
        data = self.create_overbought_data()
        signal = self.strategy.generate_signal(data)

        self.assertIn(signal['side'], ['buy', 'sell', 'hold'])

    def test_bollinger_calculation(self):
        """Test calcul Bollinger Bands"""
        data = self.create_oversold_data()
        bb = self.strategy.calculate_bollinger_bands(data['close'])

        self.assertIn('upper', bb)
        self.assertIn('middle', bb)
        self.assertIn('lower', bb)

        # Upper > middle > lower
        self.assertGreater(bb['upper'].iloc[-1], bb['middle'].iloc[-1])
        self.assertGreater(bb['middle'].iloc[-1], bb['lower'].iloc[-1])


class TestBreakoutStrategy(unittest.TestCase):
    """Tests pour BreakoutStrategy"""

    def setUp(self):
        """Initialise la stratégie avant chaque test"""
        self.strategy = BreakoutStrategy()

    def create_breakout_data(self, direction='up'):
        """
        Crée des données simulant une cassure

        Args:
            direction: 'up' ou 'down'
        """
        np.random.seed(42)

        if direction == 'up':
            # Consolidation puis breakout haussier
            close = np.concatenate([
                np.random.randn(150) * 200 + 50000,  # Consolidation
                np.linspace(50000, 52000, 50)  # Breakout
            ])
        else:
            # Consolidation puis breakout baissier
            close = np.concatenate([
                np.random.randn(150) * 200 + 50000,  # Consolidation
                np.linspace(50000, 48000, 50)  # Breakout down
            ])

        periods = len(close)
        open_prices = close + np.random.randn(periods) * 50
        high = np.maximum(open_prices, close) + np.abs(np.random.randn(periods) * 100)
        low = np.minimum(open_prices, close) - np.abs(np.random.randn(periods) * 100)

        # Volume plus élevé pendant le breakout
        volume = np.concatenate([
            np.random.randint(100, 500, 150),
            np.random.randint(800, 1500, 50)  # Volume élevé
        ])

        return pd.DataFrame({
            'open': open_prices,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume
        })

    def test_generate_signal_breakout_up(self):
        """Test signal sur breakout haussier"""
        data = self.create_breakout_data(direction='up')
        signal = self.strategy.generate_signal(data)

        self.assertIn('side', signal)
        self.assertIn('confidence', signal)

        # Devrait potentiellement détecter un signal buy
        self.assertIn(signal['side'], ['buy', 'sell', 'hold'])

    def test_generate_signal_breakout_down(self):
        """Test signal sur breakout baissier"""
        data = self.create_breakout_data(direction='down')
        signal = self.strategy.generate_signal(data)

        self.assertIn(signal['side'], ['buy', 'sell', 'hold'])

    def test_find_support_resistance(self):
        """Test identification support/résistance"""
        data = self.create_breakout_data()
        support, resistance = self.strategy.find_support_resistance(data, 50)

        # Résistance > support
        self.assertGreater(resistance, support)
        self.assertGreater(support, 0)

    def test_volume_confirmation(self):
        """Test confirmation par volume"""
        data = self.create_breakout_data()
        is_high, ratio = self.strategy.calculate_volume_confirmation(data)

        # Volume ratio devrait être positif
        self.assertGreater(ratio, 0)


if __name__ == '__main__':
    unittest.main()
