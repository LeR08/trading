"""
Order Executor Module
Gère l'exécution des ordres avec retry logic, backoff, et gestion d'erreurs Kraken
"""
import time
import logging
import json
from typing import Dict, Optional, List
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class OrderStatus(Enum):
    """États possibles d'un ordre"""
    PENDING = "pending"
    SUBMITTED = "submitted"
    FILLED = "filled"
    REJECTED = "rejected"
    FAILED = "failed"
    CANCELLED = "cancelled"


class KrakenErrorType(Enum):
    """Types d'erreurs Kraken"""
    RATE_LIMIT = "rate_limit"
    INSUFFICIENT_FUNDS = "insufficient_funds"
    INVALID_PARAMS = "invalid_params"
    PERMISSION = "permission"
    NETWORK = "network"
    UNKNOWN = "unknown"


class OrderExecutor:
    """
    Exécuteur d'ordres avec gestion d'erreurs et retries
    """

    def __init__(
        self,
        kraken_api,
        max_retries: int = 5,
        base_delay: float = 2.0,
        max_delay: float = 60.0,
        save_orders: bool = True,
        orders_file: str = "orders_log.jsonl"
    ):
        """
        Initialise l'OrderExecutor

        Args:
            kraken_api: Instance de KrakenAPI
            max_retries: Nombre max de tentatives
            base_delay: Délai initial en secondes
            max_delay: Délai maximum entre retries
            save_orders: Sauvegarder les ordres dans un fichier
            orders_file: Fichier pour sauvegarder les ordres
        """
        self.api = kraken_api
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.save_orders = save_orders
        self.orders_file = orders_file

        # Métriques
        self.total_orders = 0
        self.successful_orders = 0
        self.failed_orders = 0
        self.retried_orders = 0

    def place_order(self, signal: Dict) -> Dict:
        """
        Place un ordre basé sur le signal de trading

        Args:
            signal: Dict avec:
                - side: 'buy' ou 'sell'
                - volume: Taille de la position
                - pair: Paire de trading
                - leverage: Levier
                - price: Prix (pour limit orders)
                - tp: Take profit
                - sl: Stop loss

        Returns:
            Dict avec:
            {
                'success': bool,
                'order_id': str,
                'txid': list,
                'status': OrderStatus,
                'error': str,
                'attempts': int,
                'timestamp': str
            }
        """
        self.total_orders += 1

        # Validation du signal
        validation_ok, validation_msg = self._validate_signal(signal)
        if not validation_ok:
            return self._failed_result(validation_msg, attempts=0)

        # Tentatives avec retry logic
        last_error = None
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(
                    f"Tentative {attempt}/{self.max_retries} - "
                    f"Placement ordre {signal['side'].upper()}"
                )

                # Construire le payload de l'ordre
                order_params = self._build_order_payload(signal)

                # D'abord valider l'ordre
                validation_result = self._validate_order_with_api(order_params)
                if not validation_result['valid']:
                    # Erreur de validation non-retriable
                    error_type = self._classify_error(validation_result.get('error', []))
                    if not self._is_retriable_error(error_type):
                        return self._failed_result(
                            f"Validation échouée: {validation_result['error']}",
                            attempts=attempt
                        )

                # Placer l'ordre réel
                result = self.api.add_order(**order_params)

                if result.get('error'):
                    errors = result['error']
                    error_type = self._classify_error(errors)

                    logger.warning(f"Erreur ordre (tentative {attempt}): {errors}")

                    # Vérifier si retriable
                    if self._is_retriable_error(error_type):
                        last_error = errors
                        if attempt < self.max_retries:
                            delay = self._calculate_backoff(attempt, error_type)
                            logger.info(f"Retry dans {delay:.1f}s...")
                            time.sleep(delay)
                            self.retried_orders += 1
                            continue
                    else:
                        # Erreur non-retriable
                        return self._failed_result(
                            f"Erreur non-retriable: {errors}",
                            attempts=attempt
                        )

                # Succès!
                txid = result['result'].get('txid', [])
                descr = result['result'].get('descr', {})

                order_result = {
                    'success': True,
                    'order_id': txid[0] if txid else None,
                    'txid': txid,
                    'status': OrderStatus.SUBMITTED.value,
                    'description': descr,
                    'error': None,
                    'attempts': attempt,
                    'timestamp': datetime.utcnow().isoformat()
                }

                # Sauvegarder l'ordre
                if self.save_orders:
                    self._save_order(signal, order_result)

                self.successful_orders += 1
                logger.info(f"✅ Ordre placé avec succès: {txid}")

                return order_result

            except Exception as e:
                logger.error(f"Exception lors du placement d'ordre: {e}")
                last_error = str(e)

                # Retry sur exception réseau
                if attempt < self.max_retries:
                    delay = self._calculate_backoff(attempt, KrakenErrorType.NETWORK)
                    logger.info(f"Retry après exception dans {delay:.1f}s...")
                    time.sleep(delay)
                    self.retried_orders += 1
                    continue

        # Échec après tous les retries
        self.failed_orders += 1
        return self._failed_result(
            f"Échec après {self.max_retries} tentatives: {last_error}",
            attempts=self.max_retries
        )

    def _build_order_payload(self, signal: Dict) -> Dict:
        """
        Construit le payload pour AddOrder API

        Args:
            signal: Signal de trading

        Returns:
            Dict avec paramètres pour add_order()
        """
        params = {
            'pair': signal.get('pair', 'XBTEUR'),
            'side': signal['side'],
            'ordertype': signal.get('ordertype', 'market'),
            'volume': signal['volume']
        }

        # Prix (pour limit orders)
        if 'price' in signal and signal.get('ordertype') == 'limit':
            params['price'] = signal['price']

        # Leverage
        if 'leverage' in signal:
            params['leverage'] = signal['leverage']

        # Stop Loss et Take Profit avec Kraken conditional close
        # Kraken permet UN SEUL ordre de fermeture conditionnel par position
        # Priorité au SL pour la protection, TP géré manuellement après
        has_sl = 'sl' in signal and signal['sl']
        has_tp = 'tp' in signal and signal['tp']

        if has_sl and has_tp:
            # Les deux présents: utiliser stop-loss-limit pour combiner les deux
            # close[ordertype]=stop-loss-limit, close[price]=TP, close[price2]=SL
            params['close[ordertype]'] = 'stop-loss-limit'
            params['close[price]'] = str(signal['tp'])     # Prix limite (TP)
            params['close[price2]'] = str(signal['sl'])    # Prix trigger (SL)
        elif has_sl:
            # Seulement SL: utiliser stop-loss simple
            params['close[ordertype]'] = 'stop-loss'
            params['close[price]'] = str(signal['sl'])
        elif has_tp:
            # Seulement TP: utiliser limit
            params['close[ordertype]'] = 'limit'
            params['close[price]'] = str(signal['tp'])

        return params

    def _validate_order_with_api(self, order_params: Dict) -> Dict:
        """
        Valide l'ordre avec l'API Kraken (validate=true)

        Args:
            order_params: Paramètres de l'ordre

        Returns:
            Dict avec valid=True/False et error si applicable
        """
        try:
            # Copier les params et ajouter validation
            validation_params = order_params.copy()

            result = self.api.add_order(**validation_params, validate=True)

            if result.get('error'):
                return {
                    'valid': False,
                    'error': result['error']
                }

            return {'valid': True}

        except Exception as e:
            return {
                'valid': False,
                'error': [str(e)]
            }

    def _validate_signal(self, signal: Dict) -> tuple[bool, str]:
        """
        Valide le signal avant de placer l'ordre

        Args:
            signal: Signal à valider

        Returns:
            Tuple (is_valid, error_message)
        """
        required_fields = ['side', 'volume']

        for field in required_fields:
            if field not in signal:
                return False, f"Champ requis manquant: {field}"

        # Valider side
        if signal['side'] not in ['buy', 'sell']:
            return False, f"Side invalide: {signal['side']}"

        # Valider volume
        if signal['volume'] <= 0:
            return False, f"Volume invalide: {signal['volume']}"

        return True, ""

    def _classify_error(self, errors: List[str]) -> KrakenErrorType:
        """
        Classifie le type d'erreur Kraken

        Args:
            errors: Liste d'erreurs de l'API

        Returns:
            Type d'erreur
        """
        if not errors:
            return KrakenErrorType.UNKNOWN

        error_str = ' '.join(errors).lower()

        # Rate limit
        if 'rate limit' in error_str or 'eapi:rate limit' in error_str:
            return KrakenErrorType.RATE_LIMIT

        # Fonds insuffisants
        if 'insufficient' in error_str or 'balance' in error_str:
            return KrakenErrorType.INSUFFICIENT_FUNDS

        # Paramètres invalides
        if 'invalid' in error_str or 'egeneral:invalid' in error_str:
            return KrakenErrorType.INVALID_PARAMS

        # Permission
        if 'permission' in error_str or 'epermission' in error_str:
            return KrakenErrorType.PERMISSION

        # Network/timeout
        if 'timeout' in error_str or 'connection' in error_str:
            return KrakenErrorType.NETWORK

        return KrakenErrorType.UNKNOWN

    def _is_retriable_error(self, error_type: KrakenErrorType) -> bool:
        """
        Détermine si une erreur justifie un retry

        Args:
            error_type: Type d'erreur

        Returns:
            True si retriable
        """
        retriable_errors = {
            KrakenErrorType.RATE_LIMIT,
            KrakenErrorType.NETWORK,
            KrakenErrorType.UNKNOWN
        }

        return error_type in retriable_errors

    def _calculate_backoff(self, attempt: int, error_type: KrakenErrorType) -> float:
        """
        Calcule le délai de backoff exponentiel

        Args:
            attempt: Numéro de tentative
            error_type: Type d'erreur

        Returns:
            Délai en secondes
        """
        # Backoff exponentiel: base_delay * 2^(attempt-1)
        delay = self.base_delay * (2 ** (attempt - 1))

        # Rate limit: délai plus long
        if error_type == KrakenErrorType.RATE_LIMIT:
            delay *= 2

        # Cap au max_delay
        delay = min(delay, self.max_delay)

        # Ajouter un petit jitter pour éviter la synchronisation
        import random
        jitter = random.uniform(0, delay * 0.1)
        delay += jitter

        return delay

    def _failed_result(self, error: str, attempts: int) -> Dict:
        """
        Retourne un résultat d'échec

        Args:
            error: Message d'erreur
            attempts: Nombre de tentatives

        Returns:
            Dict avec success=False
        """
        return {
            'success': False,
            'order_id': None,
            'txid': [],
            'status': OrderStatus.FAILED.value,
            'error': error,
            'attempts': attempts,
            'timestamp': datetime.utcnow().isoformat()
        }

    def _save_order(self, signal: Dict, result: Dict):
        """
        Sauvegarde l'ordre dans un fichier log (idempotent)

        Args:
            signal: Signal de trading
            result: Résultat de l'ordre
        """
        try:
            order_log = {
                'timestamp': result['timestamp'],
                'signal': signal,
                'result': result
            }

            with open(self.orders_file, 'a') as f:
                f.write(json.dumps(order_log) + '\n')

        except Exception as e:
            logger.error(f"Erreur sauvegarde ordre: {e}")

    def get_statistics(self) -> Dict:
        """
        Retourne les statistiques de l'executor

        Returns:
            Dict avec métriques
        """
        success_rate = (
            (self.successful_orders / self.total_orders * 100)
            if self.total_orders > 0
            else 0
        )

        return {
            'total_orders': self.total_orders,
            'successful_orders': self.successful_orders,
            'failed_orders': self.failed_orders,
            'retried_orders': self.retried_orders,
            'success_rate': round(success_rate, 2)
        }
