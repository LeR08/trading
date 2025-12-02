"""
Unit tests for risk manager
"""
import unittest
from src.risk_engine.risk_manager import RiskManager, RiskCheckStatus


class TestRiskManager(unittest.TestCase):
    """Test risk manager"""

    def setUp(self):
        """Set up test risk manager"""
        self.risk_manager = RiskManager(
            risk_per_trade=0.01,
            max_total_exposure=0.05,
            leverage=3,
            max_daily_drawdown=0.03,
            max_total_drawdown=0.10,
            max_concurrent_trades=3
        )

    def test_position_size_calculation_long(self):
        """Test position size calculation for long"""
        equity = 10000.0
        entry_price = 50000.0
        stop_loss = 49000.0
        take_profit = 51000.0

        position = self.risk_manager.calculate_position_size(
            equity=equity,
            entry_price=entry_price,
            stop_loss_price=stop_loss,
            take_profit_price=take_profit,
            direction="long"
        )

        # Check basic validations
        self.assertGreater(position.volume, 0)
        self.assertGreater(position.notional_value, 0)
        self.assertGreater(position.margin_required, 0)

        # Risk amount should be ~1% of equity
        self.assertAlmostEqual(position.risk_amount, equity * 0.01, delta=1.0)

        # Margin should be notional / leverage
        expected_margin = position.notional_value / 3
        self.assertAlmostEqual(position.margin_required, expected_margin, delta=0.01)

    def test_position_size_calculation_short(self):
        """Test position size calculation for short"""
        equity = 10000.0
        entry_price = 50000.0
        stop_loss = 51000.0
        take_profit = 49000.0

        position = self.risk_manager.calculate_position_size(
            equity=equity,
            entry_price=entry_price,
            stop_loss_price=stop_loss,
            take_profit_price=take_profit,
            direction="short"
        )

        self.assertGreater(position.volume, 0)
        self.assertGreater(position.notional_value, 0)

    def test_margin_check_sufficient(self):
        """Test margin check with sufficient funds"""
        trade_balance = {
            "e": "10000.0",  # equity
            "mf": "8000.0",  # free margin
            "m": "2000.0"    # used margin
        }

        required_margin = 1000.0

        result = self.risk_manager.check_margin_availability(trade_balance, required_margin)

        self.assertTrue(result.approved)
        self.assertEqual(result.status, RiskCheckStatus.APPROVED)

    def test_margin_check_insufficient(self):
        """Test margin check with insufficient funds"""
        trade_balance = {
            "e": "10000.0",
            "mf": "500.0",
            "m": "9500.0"
        }

        required_margin = 1000.0

        result = self.risk_manager.check_margin_availability(trade_balance, required_margin)

        self.assertFalse(result.approved)
        self.assertEqual(result.status, RiskCheckStatus.REJECTED)

    def test_exposure_limit_check(self):
        """Test exposure limit check"""
        equity = 10000.0
        current_exposure = 300.0
        new_position_value = 200.0

        # Should pass (total 5% of equity)
        result = self.risk_manager.check_exposure_limit(current_exposure, new_position_value, equity)
        self.assertTrue(result.approved)

        # Should fail
        new_position_value = 1000.0
        result = self.risk_manager.check_exposure_limit(current_exposure, new_position_value, equity)
        self.assertFalse(result.approved)

    def test_concurrent_trades_check(self):
        """Test concurrent trades limit"""
        # Should pass
        result = self.risk_manager.check_concurrent_trades(2)
        self.assertTrue(result.approved)

        # Should fail
        result = self.risk_manager.check_concurrent_trades(3)
        self.assertFalse(result.approved)

    def test_circuit_breaker(self):
        """Test circuit breaker"""
        # Initially should be inactive
        result = self.risk_manager.check_circuit_breaker()
        self.assertTrue(result.approved)

        # Activate circuit breaker
        self.risk_manager.activate_circuit_breaker("Test reason")

        # Should now be rejected
        result = self.risk_manager.check_circuit_breaker()
        self.assertFalse(result.approved)

        # Deactivate
        self.risk_manager.deactivate_circuit_breaker()
        result = self.risk_manager.check_circuit_breaker()
        self.assertTrue(result.approved)

    def test_stop_loss_calculation(self):
        """Test stop loss calculation"""
        entry_price = 50000.0
        atr = 500.0
        multiplier = 1.0

        # Long
        sl_long = self.risk_manager.calculate_stop_loss(entry_price, atr, "long", multiplier)
        self.assertEqual(sl_long, entry_price - atr * multiplier)

        # Short
        sl_short = self.risk_manager.calculate_stop_loss(entry_price, atr, "short", multiplier)
        self.assertEqual(sl_short, entry_price + atr * multiplier)

    def test_take_profit_calculation(self):
        """Test take profit calculation"""
        entry_price = 50000.0
        stop_loss_long = 49000.0
        reward_ratio = 1.0

        # Long
        tp_long = self.risk_manager.calculate_take_profit(entry_price, stop_loss_long, "long", reward_ratio)
        expected_tp = entry_price + (entry_price - stop_loss_long) * reward_ratio
        self.assertAlmostEqual(tp_long, expected_tp)


if __name__ == '__main__':
    unittest.main()
