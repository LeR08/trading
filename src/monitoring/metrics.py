"""
Prometheus Metrics Module
Exporte les métriques du bot pour monitoring via Prometheus
"""
from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST
from flask import Flask, Response
import logging
from typing import Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class TradingMetrics:
    """
    Gestion des métriques Prometheus pour le bot de trading
    """

    def __init__(self):
        """Initialise les métriques Prometheus"""

        # Métriques de positions
        self.open_positions = Gauge(
            'trading_open_positions_total',
            'Nombre de positions ouvertes'
        )

        self.positions_long = Gauge(
            'trading_positions_long',
            'Nombre de positions long ouvertes'
        )

        self.positions_short = Gauge(
            'trading_positions_short',
            'Nombre de positions short ouvertes'
        )

        # Métriques de marge
        self.used_margin = Gauge(
            'trading_used_margin',
            'Marge utilisée actuellement'
        )

        self.free_margin = Gauge(
            'trading_free_margin',
            'Marge libre disponible'
        )

        self.margin_level = Gauge(
            'trading_margin_level_percent',
            'Niveau de marge en pourcentage'
        )

        # Métriques d\'équité
        self.equity = Gauge(
            'trading_equity',
            'Équité actuelle du compte'
        )

        self.balance = Gauge(
            'trading_balance',
            'Balance du compte'
        )

        # Métriques de P&L
        self.unrealized_pnl = Gauge(
            'trading_unrealized_pnl',
            'P&L non réalisé'
        )

        self.realized_pnl = Gauge(
            'trading_realized_pnl',
            'P&L réalisé (total)'
        )

        self.daily_pnl = Gauge(
            'trading_daily_pnl',
            'P&L du jour'
        )

        # Métriques de trades
        self.total_trades = Counter(
            'trading_total_trades',
            'Nombre total de trades exécutés'
        )

        self.winning_trades = Counter(
            'trading_winning_trades',
            'Nombre de trades gagnants'
        )

        self.losing_trades = Counter(
            'trading_losing_trades',
            'Nombre de trades perdants'
        )

        # Métriques d'ordres
        self.orders_placed = Counter(
            'trading_orders_placed_total',
            'Nombre d\'ordres placés',
            ['status']  # status: success, failed, rejected
        )

        self.order_latency = Histogram(
            'trading_order_latency_seconds',
            'Latence de placement d\'ordre en secondes'
        )

        # Métriques de stratégie
        self.signal_strength = Gauge(
            'trading_signal_strength',
            'Force du signal actuel (0-1)'
        )

        self.signal_type = Gauge(
            'trading_signal_type',
            'Type de signal (-1=sell, 0=hold, 1=buy)'
        )

        # Métriques de circuit breaker
        self.circuit_breaker_state = Gauge(
            'trading_circuit_breaker_state',
            'État du circuit breaker (0=closed, 1=open, 2=half_open)'
        )

        self.consecutive_losses = Gauge(
            'trading_consecutive_losses',
            'Nombre de pertes consécutives'
        )

        self.drawdown = Gauge(
            'trading_drawdown_percent',
            'Drawdown actuel en pourcentage'
        )

        # Métriques système
        self.bot_uptime_seconds = Gauge(
            'trading_bot_uptime_seconds',
            'Durée de fonctionnement du bot en secondes'
        )

        self.last_update_timestamp = Gauge(
            'trading_last_update_timestamp',
            'Timestamp de la dernière mise à jour'
        )

        self.api_errors = Counter(
            'trading_api_errors_total',
            'Nombre d\'erreurs API',
            ['error_type']
        )

        # État du bot
        self.bot_start_time = datetime.now()

    def update_positions(self, positions_data: Dict):
        """
        Met à jour les métriques de positions

        Args:
            positions_data: Dict avec infos positions
                - total: nombre total
                - long: nombre long
                - short: nombre short
        """
        self.open_positions.set(positions_data.get('total', 0))
        self.positions_long.set(positions_data.get('long', 0))
        self.positions_short.set(positions_data.get('short', 0))

    def update_margin(self, margin_data: Dict):
        """
        Met à jour les métriques de marge

        Args:
            margin_data: Dict depuis MarginChecker
                - used_margin
                - free_margin
                - margin_level
        """
        self.used_margin.set(margin_data.get('used_margin', 0))
        self.free_margin.set(margin_data.get('free_margin', 0))
        self.margin_level.set(margin_data.get('margin_level', 0))

    def update_equity(self, equity: float, balance: float):
        """
        Met à jour les métriques d'équité

        Args:
            equity: Équité actuelle
            balance: Balance actuelle
        """
        self.equity.set(equity)
        self.balance.set(balance)

    def update_pnl(self, unrealized: float, realized: float, daily: float):
        """
        Met à jour les métriques de P&L

        Args:
            unrealized: P&L non réalisé
            realized: P&L réalisé total
            daily: P&L du jour
        """
        self.unrealized_pnl.set(unrealized)
        self.realized_pnl.set(realized)
        self.daily_pnl.set(daily)

    def record_trade(self, is_winner: bool):
        """
        Enregistre un trade

        Args:
            is_winner: True si trade gagnant
        """
        self.total_trades.inc()
        if is_winner:
            self.winning_trades.inc()
        else:
            self.losing_trades.inc()

    def record_order(self, status: str, latency: Optional[float] = None):
        """
        Enregistre un ordre

        Args:
            status: 'success', 'failed', ou 'rejected'
            latency: Temps d'exécution en secondes
        """
        self.orders_placed.labels(status=status).inc()

        if latency is not None:
            self.order_latency.observe(latency)

    def update_signal(self, signal: Dict):
        """
        Met à jour les métriques de signal

        Args:
            signal: Dict avec side et confidence
        """
        # Convertir side en numérique
        signal_map = {
            'sell': -1,
            'hold': 0,
            'buy': 1
        }
        signal_value = signal_map.get(signal.get('side', 'hold'), 0)

        self.signal_type.set(signal_value)
        self.signal_strength.set(signal.get('confidence', 0))

    def update_circuit_breaker(self, cb_data: Dict):
        """
        Met à jour les métriques du circuit breaker

        Args:
            cb_data: Dict depuis CircuitBreaker.check()
        """
        # Convertir state en numérique
        state_map = {
            'closed': 0,
            'open': 1,
            'half_open': 2
        }
        state_value = state_map.get(cb_data.get('state', 'closed'), 0)

        self.circuit_breaker_state.set(state_value)
        self.consecutive_losses.set(cb_data.get('consecutive_losses', 0))
        self.drawdown.set(abs(cb_data.get('current_drawdown', 0)) * 100)

    def update_system(self):
        """Met à jour les métriques système"""
        uptime = (datetime.now() - self.bot_start_time).total_seconds()
        self.bot_uptime_seconds.set(uptime)
        self.last_update_timestamp.set(datetime.now().timestamp())

    def record_api_error(self, error_type: str):
        """
        Enregistre une erreur API

        Args:
            error_type: Type d'erreur (rate_limit, network, etc.)
        """
        self.api_errors.labels(error_type=error_type).inc()

    def get_metrics(self) -> bytes:
        """
        Retourne les métriques au format Prometheus

        Returns:
            Métriques encodées pour Prometheus
        """
        return generate_latest()


# Instance globale pour faciliter l'accès
_metrics_instance: Optional[TradingMetrics] = None


def get_metrics_instance() -> TradingMetrics:
    """
    Retourne l'instance singleton des métriques

    Returns:
        Instance TradingMetrics
    """
    global _metrics_instance
    if _metrics_instance is None:
        _metrics_instance = TradingMetrics()
    return _metrics_instance


def create_metrics_server(host: str = '0.0.0.0', port: int = 9090) -> Flask:
    """
    Crée un serveur Flask pour exposer les métriques

    Args:
        host: Host à écouter
        port: Port à écouter

    Returns:
        App Flask
    """
    app = Flask(__name__)
    metrics = get_metrics_instance()

    @app.route('/metrics')
    def metrics_endpoint():
        """Endpoint pour Prometheus scraping"""
        return Response(metrics.get_metrics(), mimetype=CONTENT_TYPE_LATEST)

    @app.route('/health')
    def health_endpoint():
        """Endpoint de santé"""
        return {'status': 'healthy', 'timestamp': datetime.now().isoformat()}

    logger.info(f"Serveur de métriques configuré sur {host}:{port}")

    return app


def run_metrics_server(host: str = '0.0.0.0', port: int = 9090):
    """
    Lance le serveur de métriques

    Args:
        host: Host à écouter
        port: Port à écouter
    """
    app = create_metrics_server(host, port)
    logger.info(f"🚀 Démarrage serveur métriques sur {host}:{port}")
    app.run(host=host, port=port, threaded=True)
