"""
Tests unitaires pour le module risk_engine
"""
import unittest
import sys
sys.path.insert(0, '/home/user/trading')

from src.risk_engine.position_sizer import PositionSizer
from src.risk_engine.circuit_breaker import CircuitBreaker, CircuitBreakerState
from src.risk_engine.margin_checker import MarginChecker


class TestPositionSizer(unittest.TestCase):
    """Tests pour PositionSizer"""

    def setUp(self):
        """Initialise le sizer avant chaque test"""
        self.sizer = PositionSizer(
            default_risk_pct=0.03,
            max_exposure_pct=0.10,
            default_leverage=3
        )

    def test_calc_size_basic(self):
        """Test calcul de taille basique"""
        result = self.sizer.calc_size(
            equity=10000,
            price=50000,
            risk_pct=0.03,
            leverage=3,
            stop_loss_pct=0.03
        )

        self.assertTrue(result['valid'])
        self.assertGreater(result['volume'], 0)
        self.assertEqual(result['leverage'], 3)
        self.assertLessEqual(result['margin_required'], 10000)

    def test_calc_size_insufficient_equity(self):
        """Test avec équité insuffisante"""
        result = self.sizer.calc_size(
            equity=0,
            price=50000,
            risk_pct=0.03,
            leverage=3
        )

        self.assertFalse(result['valid'])
        self.assertIn('équité', result['reason'].lower())

    def test_calc_size_excessive_exposure(self):
        """Test exposition excessive"""
        result = self.sizer.calc_size(
            equity=1000,
            price=50000,
            risk_pct=0.50,  # 50% risque = trop élevé
            leverage=3
        )

        # Devrait être invalide car exposition > max_exposure
        self.assertFalse(result['valid'])

    def test_calc_size_with_asset_pair_validation(self):
        """Test validation avec contraintes AssetPairs"""
        asset_pair_info = {
            'ordermin': '0.001',
            'lot_decimals': 8
        }

        result = self.sizer.calc_size(
            equity=10000,
            price=50000,
            risk_pct=0.01,
            leverage=3,
            stop_loss_pct=0.03,
            asset_pair_info=asset_pair_info
        )

        self.assertTrue(result['valid'])
        self.assertGreaterEqual(result['volume'], 0.001)

    def test_total_exposure_calculation(self):
        """Test calcul exposition totale"""
        open_positions = [
            {'position_value': 5000},
            {'position_value': 3000}
        ]

        exposure = self.sizer.calculate_total_exposure(open_positions, 10000)

        self.assertEqual(exposure, 0.8)  # 8000/10000

    def test_can_open_new_position(self):
        """Test vérification ouverture nouvelle position"""
        open_positions = [
            {'position_value': 2000}
        ]

        can_open, reason = self.sizer.can_open_new_position(
            open_positions,
            equity=10000,
            new_position_value=1000
        )

        self.assertTrue(can_open)


class TestCircuitBreaker(unittest.TestCase):
    """Tests pour CircuitBreaker"""

    def setUp(self):
        """Initialise le circuit breaker avant chaque test"""
        self.cb = CircuitBreaker(
            max_drawdown_pct=0.15,
            max_daily_loss_pct=0.05,
            max_consecutive_losses=5,
            cooldown_minutes=1  # Court pour les tests
        )
        self.cb.initialize(10000)

    def test_initial_state(self):
        """Test état initial"""
        result = self.cb.check(10000)

        self.assertTrue(result['trading_allowed'])
        self.assertEqual(result['state'], CircuitBreakerState.CLOSED.value)
        self.assertEqual(result['consecutive_losses'], 0)

    def test_drawdown_trigger(self):
        """Test déclenchement par drawdown excessif"""
        # Simuler une grosse perte (>15%)
        result = self.cb.check(8400)  # 16% de perte

        self.assertFalse(result['trading_allowed'])
        self.assertEqual(result['state'], CircuitBreakerState.OPEN.value)
        self.assertLess(result['current_drawdown'], -0.15)

    def test_daily_loss_trigger(self):
        """Test déclenchement par perte journalière"""
        self.cb.daily_start_equity = 10000

        # Perte de 6% dans la journée
        result = self.cb.check(9400)

        self.assertFalse(result['trading_allowed'])
        self.assertEqual(result['state'], CircuitBreakerState.OPEN.value)

    def test_consecutive_losses_trigger(self):
        """Test déclenchement par pertes consécutives"""
        # Enregistrer 5 pertes
        for _ in range(5):
            self.cb.record_trade_result(pnl=-100, equity_after=9500)

        result = self.cb.check(9500)

        self.assertFalse(result['trading_allowed'])
        self.assertEqual(result['consecutive_losses'], 5)

    def test_reset_on_win(self):
        """Test reset des pertes consécutives sur gain"""
        # 3 pertes
        for _ in range(3):
            self.cb.record_trade_result(pnl=-100, equity_after=9700)

        self.assertEqual(self.cb.consecutive_losses, 3)

        # 1 gain
        self.cb.record_trade_result(pnl=200, equity_after=9900)

        self.assertEqual(self.cb.consecutive_losses, 0)


class TestMarginChecker(unittest.TestCase):
    """Tests pour MarginChecker"""

    def setUp(self):
        """Initialise le margin checker avant chaque test"""
        self.checker = MarginChecker(
            min_margin_level=150.0,
            warning_margin_level=200.0,
            min_free_margin_pct=0.20
        )

    def test_check_margin_sufficient(self):
        """Test vérification marge suffisante"""
        trade_balance = {
            'e': '10000',    # equity
            'm': '4000',     # margin used
            'mf': '6000',    # free margin
            'ml': '250'      # margin level 250%
        }

        result = self.checker.check_margin(trade_balance)

        self.assertTrue(result['sufficient'])
        self.assertEqual(result['margin_level'], 250.0)
        self.assertFalse(result['warning'])

    def test_check_margin_insufficient(self):
        """Test marge insuffisante"""
        trade_balance = {
            'e': '10000',
            'm': '8000',
            'mf': '2000',
            'ml': '125'  # Sous le minimum de 150%
        }

        result = self.checker.check_margin(trade_balance)

        self.assertFalse(result['sufficient'])
        self.assertEqual(result['margin_level'], 125.0)

    def test_check_margin_warning_zone(self):
        """Test zone d'avertissement"""
        trade_balance = {
            'e': '10000',
            'm': '5500',
            'mf': '4500',
            'ml': '181.82'  # Entre 150 et 200
        }

        result = self.checker.check_margin(trade_balance)

        self.assertTrue(result['sufficient'])
        self.assertTrue(result['warning'])

    def test_can_open_position(self):
        """Test vérification ouverture position"""
        trade_balance = {
            'e': '10000',
            'm': '3000',
            'mf': '7000'
        }

        can_open, reason = self.checker.can_open_position(
            trade_balance,
            additional_margin_required=2000
        )

        self.assertTrue(can_open)

    def test_cannot_open_insufficient_free_margin(self):
        """Test refus si free margin insuffisant"""
        trade_balance = {
            'e': '10000',
            'm': '8000',
            'mf': '2000'
        }

        can_open, reason = self.checker.can_open_position(
            trade_balance,
            additional_margin_required=3000  # Plus que free margin
        )

        self.assertFalse(can_open)
        self.assertIn('insuffisant', reason.lower())

    def test_margin_call_distance(self):
        """Test calcul distance au margin call"""
        trade_balance = {
            'e': '10000',
            'm': '4000',
            'ml': '250'
        }

        result = self.checker.get_margin_call_distance(trade_balance)

        self.assertGreater(result['distance_pct'], 0)
        self.assertTrue(result['safe'])


if __name__ == '__main__':
    unittest.main()
