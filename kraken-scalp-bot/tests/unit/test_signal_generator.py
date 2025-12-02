"""
Unit tests for signal generator
"""
import unittest
from src.signal_engine.signal_generator import SignalGenerator, Direction
from src.indicators.technical_indicators import IndicatorSignal


class TestSignalGenerator(unittest.TestCase):
    """Test signal generator"""

    def setUp(self):
        """Set up test signal generator"""
        self.weights = {
            'ind1': 0.3,
            'ind2': 0.3,
            'ind3': 0.2,
            'ind4': 0.2,
        }
        self.signal_gen = SignalGenerator(weights=self.weights, confidence_threshold=66.0)

    def test_weight_normalization(self):
        """Test that weights are normalized"""
        total = sum(self.signal_gen.weights.values())
        self.assertAlmostEqual(total, 1.0, places=5)

    def test_raw_score_calculation(self):
        """Test raw score calculation"""
        signals = {
            'ind1': IndicatorSignal('ind1', 100, 1.0, 0.8),
            'ind2': IndicatorSignal('ind2', 50, 0.5, 0.6),
            'ind3': IndicatorSignal('ind3', 30, -1.0, 0.9),
            'ind4': IndicatorSignal('ind4', 70, 0.0, 0.0),
        }

        score = self.signal_gen.calculate_raw_score(signals)

        # Expected: 0.3*1.0 + 0.3*0.5 + 0.2*(-1.0) + 0.2*0.0 = 0.25
        expected = 0.3 * 1.0 + 0.3 * 0.5 + 0.2 * (-1.0) + 0.2 * 0.0
        self.assertAlmostEqual(score, expected, places=2)

    def test_confidence_calculation(self):
        """Test confidence calculation"""
        # Confidence should be abs(raw_score) * 100
        self.assertEqual(self.signal_gen.calculate_confidence(0.7), 70.0)
        self.assertEqual(self.signal_gen.calculate_confidence(-0.5), 50.0)
        self.assertEqual(self.signal_gen.calculate_confidence(0.0), 0.0)

    def test_direction_determination(self):
        """Test direction determination"""
        # High confidence, positive score -> LONG
        direction = self.signal_gen.determine_direction(0.7, 70.0)
        self.assertEqual(direction, Direction.LONG)

        # High confidence, negative score -> SHORT
        direction = self.signal_gen.determine_direction(-0.7, 70.0)
        self.assertEqual(direction, Direction.SHORT)

        # Low confidence -> NEUTRAL
        direction = self.signal_gen.determine_direction(0.5, 50.0)
        self.assertEqual(direction, Direction.NEUTRAL)

    def test_signal_generation(self):
        """Test full signal generation"""
        signals = {
            'ind1': IndicatorSignal('ind1', 100, 1.0, 0.8),
            'ind2': IndicatorSignal('ind2', 50, 1.0, 0.7),
            'ind3': IndicatorSignal('ind3', 30, 0.5, 0.6),
            'ind4': IndicatorSignal('ind4', 70, 1.0, 0.9),
        }

        trading_signal = self.signal_gen.generate_signal(signals, timeframe=3, timestamp=1234567890)

        self.assertIsNotNone(trading_signal)
        self.assertIn(trading_signal.direction, [Direction.LONG, Direction.SHORT, Direction.NEUTRAL])
        self.assertTrue(0 <= trading_signal.confidence <= 100)
        self.assertTrue(-1 <= trading_signal.raw_score <= 1)
        self.assertEqual(trading_signal.timeframe, 3)

    def test_combine_timeframes_agreement(self):
        """Test combining timeframes when they agree"""
        signals = {
            3: self._create_signal(Direction.LONG, 70.0, 3),
            15: self._create_signal(Direction.LONG, 75.0, 15),
        }

        combined = self.signal_gen.combine_timeframes(signals, primary_timeframe=3)

        self.assertIsNotNone(combined)
        self.assertEqual(combined.direction, Direction.LONG)

    def test_combine_timeframes_conflict(self):
        """Test combining timeframes when they conflict"""
        signals = {
            3: self._create_signal(Direction.LONG, 70.0, 3),
            15: self._create_signal(Direction.SHORT, 75.0, 15),
        }

        combined = self.signal_gen.combine_timeframes(signals, primary_timeframe=3)

        self.assertIsNotNone(combined)
        self.assertEqual(combined.direction, Direction.NEUTRAL)

    def test_combine_timeframes_neutral_higher(self):
        """Test combining when higher timeframe is neutral"""
        signals = {
            3: self._create_signal(Direction.LONG, 70.0, 3),
            15: self._create_signal(Direction.NEUTRAL, 50.0, 15),
        }

        combined = self.signal_gen.combine_timeframes(signals, primary_timeframe=3)

        self.assertIsNotNone(combined)
        self.assertEqual(combined.direction, Direction.LONG)

    def _create_signal(self, direction, confidence, timeframe):
        """Helper to create a trading signal"""
        from src.signal_engine.signal_generator import TradingSignal

        raw_score = confidence / 100 if direction == Direction.LONG else -confidence / 100 if direction == Direction.SHORT else 0

        return TradingSignal(
            direction=direction,
            confidence=confidence,
            raw_score=raw_score,
            signals={},
            timeframe=timeframe,
            timestamp=1234567890,
            metadata={}
        )


if __name__ == '__main__':
    unittest.main()
