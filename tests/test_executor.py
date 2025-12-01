"""
Tests unitaires pour le module executor
"""
import unittest
from unittest.mock import Mock, patch
import sys
sys.path.insert(0, '/home/user/trading')

from src.executor.order_executor import OrderExecutor, OrderStatus, KrakenErrorType


class TestOrderExecutor(unittest.TestCase):
    """Tests pour OrderExecutor"""

    def setUp(self):
        """Initialise l'executor avant chaque test"""
        self.mock_api = Mock()
        self.executor = OrderExecutor(
            kraken_api=self.mock_api,
            max_retries=3,
            base_delay=0.1,  # Court pour tests
            save_orders=False
        )

    def test_place_order_success(self):
        """Test placement d'ordre réussi"""
        # Mock réponse API succès
        self.mock_api.add_order.return_value = {
            'error': [],
            'result': {
                'txid': ['ORDER123'],
                'descr': {'order': 'buy 0.1 XBTEUR'}
            }
        }

        signal = {
            'side': 'buy',
            'volume': 0.1,
            'pair': 'XBTEUR',
            'leverage': 3
        }

        result = self.executor.place_order(signal)

        self.assertTrue(result['success'])
        self.assertEqual(result['order_id'], 'ORDER123')
        self.assertEqual(result['status'], OrderStatus.SUBMITTED.value)
        self.assertEqual(result['attempts'], 1)
        self.assertIsNone(result['error'])

    def test_place_order_validation_failure(self):
        """Test échec validation du signal"""
        signal = {
            'side': 'invalid',  # Side invalide
            'volume': 0.1
        }

        result = self.executor.place_order(signal)

        self.assertFalse(result['success'])
        self.assertEqual(result['status'], OrderStatus.FAILED.value)
        self.assertIn('invalide', result['error'].lower())

    def test_place_order_insufficient_volume(self):
        """Test volume invalide"""
        signal = {
            'side': 'buy',
            'volume': 0  # Volume invalide
        }

        result = self.executor.place_order(signal)

        self.assertFalse(result['success'])
        self.assertIn('volume', result['error'].lower())

    def test_place_order_api_error_retriable(self):
        """Test erreur API retriable (rate limit)"""
        # Première tentative: rate limit
        # Deuxième tentative: succès
        self.mock_api.add_order.side_effect = [
            {
                'error': ['EAPI:Rate limit exceeded'],
                'result': None
            },
            {
                'error': [],
                'result': {
                    'txid': ['ORDER456'],
                    'descr': {}
                }
            }
        ]

        signal = {
            'side': 'buy',
            'volume': 0.1,
            'pair': 'XBTEUR'
        }

        result = self.executor.place_order(signal)

        # Devrait réussir après retry
        self.assertTrue(result['success'])
        self.assertEqual(result['attempts'], 2)
        self.assertEqual(self.mock_api.add_order.call_count, 2)

    def test_place_order_api_error_non_retriable(self):
        """Test erreur API non-retriable (permission)"""
        self.mock_api.add_order.return_value = {
            'error': ['EPermission:Invalid API key'],
            'result': None
        }

        signal = {
            'side': 'buy',
            'volume': 0.1,
            'pair': 'XBTEUR'
        }

        result = self.executor.place_order(signal)

        # Devrait échouer sans retry
        self.assertFalse(result['success'])
        self.assertEqual(result['attempts'], 1)
        self.assertIn('permission', result['error'].lower())

    def test_place_order_max_retries_exceeded(self):
        """Test échec après max retries"""
        # Toutes les tentatives échouent
        self.mock_api.add_order.return_value = {
            'error': ['Network timeout'],
            'result': None
        }

        signal = {
            'side': 'buy',
            'volume': 0.1,
            'pair': 'XBTEUR'
        }

        result = self.executor.place_order(signal)

        self.assertFalse(result['success'])
        self.assertEqual(result['attempts'], 3)  # max_retries = 3
        self.assertEqual(self.mock_api.add_order.call_count, 3)

    def test_classify_error_rate_limit(self):
        """Test classification erreur rate limit"""
        errors = ['EAPI:Rate limit exceeded']
        error_type = self.executor._classify_error(errors)

        self.assertEqual(error_type, KrakenErrorType.RATE_LIMIT)

    def test_classify_error_insufficient_funds(self):
        """Test classification fonds insuffisants"""
        errors = ['EGeneral:Insufficient funds']
        error_type = self.executor._classify_error(errors)

        self.assertEqual(error_type, KrakenErrorType.INSUFFICIENT_FUNDS)

    def test_classify_error_invalid_params(self):
        """Test classification paramètres invalides"""
        errors = ['EGeneral:Invalid arguments']
        error_type = self.executor._classify_error(errors)

        self.assertEqual(error_type, KrakenErrorType.INVALID_PARAMS)

    def test_is_retriable_error(self):
        """Test détermination erreurs retriables"""
        # Rate limit est retriable
        self.assertTrue(
            self.executor._is_retriable_error(KrakenErrorType.RATE_LIMIT)
        )

        # Network est retriable
        self.assertTrue(
            self.executor._is_retriable_error(KrakenErrorType.NETWORK)
        )

        # Permission n'est pas retriable
        self.assertFalse(
            self.executor._is_retriable_error(KrakenErrorType.PERMISSION)
        )

        # Insufficient funds n'est pas retriable
        self.assertFalse(
            self.executor._is_retriable_error(KrakenErrorType.INSUFFICIENT_FUNDS)
        )

    def test_calculate_backoff(self):
        """Test calcul backoff exponentiel"""
        # Premier retry
        delay1 = self.executor._calculate_backoff(1, KrakenErrorType.NETWORK)
        # Deuxième retry
        delay2 = self.executor._calculate_backoff(2, KrakenErrorType.NETWORK)

        # Le délai devrait augmenter exponentiellement
        self.assertGreater(delay2, delay1)

        # Rate limit devrait avoir un délai plus long
        delay_rate_limit = self.executor._calculate_backoff(1, KrakenErrorType.RATE_LIMIT)
        delay_network = self.executor._calculate_backoff(1, KrakenErrorType.NETWORK)

        self.assertGreater(delay_rate_limit, delay_network)

    def test_build_order_payload(self):
        """Test construction payload ordre"""
        signal = {
            'side': 'buy',
            'volume': 0.1,
            'pair': 'XBTEUR',
            'ordertype': 'market',
            'leverage': 3,
            'tp': 52000,
            'sl': 48000
        }

        payload = self.executor._build_order_payload(signal)

        self.assertEqual(payload['side'], 'buy')
        self.assertEqual(payload['volume'], 0.1)
        self.assertEqual(payload['pair'], 'XBTEUR')
        self.assertEqual(payload['leverage'], 3)
        self.assertEqual(payload['close_ordertype'], 'limit')
        self.assertEqual(payload['close_price'], 52000)

    def test_statistics(self):
        """Test statistiques executor"""
        # Simuler quelques ordres
        self.executor.total_orders = 10
        self.executor.successful_orders = 8
        self.executor.failed_orders = 2
        self.executor.retried_orders = 3

        stats = self.executor.get_statistics()

        self.assertEqual(stats['total_orders'], 10)
        self.assertEqual(stats['successful_orders'], 8)
        self.assertEqual(stats['failed_orders'], 2)
        self.assertEqual(stats['retried_orders'], 3)
        self.assertEqual(stats['success_rate'], 80.0)


if __name__ == '__main__':
    unittest.main()
