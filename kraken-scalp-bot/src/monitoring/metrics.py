"""
Monitoring and Metrics - Prometheus metrics and alerting
"""
from prometheus_client import Counter, Gauge, Histogram, start_http_server
import logging

logger = logging.getLogger(__name__)


class BotMetrics:
    """
    Bot metrics for Prometheus

    Exposes:
    - Trade counters
    - P&L gauges
    - Signal confidence
    - API latency
    - Error rates
    """

    def __init__(self):
        """Initialize metrics"""

        # Trade metrics
        self.trades_total = Counter(
            'bot_trades_total',
            'Total number of trades',
            ['direction', 'outcome']
        )

        self.trades_pnl = Gauge(
            'bot_pnl_total',
            'Total P&L',
            ['type']  # realized, unrealized
        )

        self.equity = Gauge(
            'bot_equity',
            'Current equity'
        )

        self.margin_level = Gauge(
            'bot_margin_level',
            'Margin level percentage'
        )

        # Signal metrics
        self.signal_confidence = Gauge(
            'bot_signal_confidence',
            'Current signal confidence',
            ['timeframe']
        )

        self.signal_direction = Gauge(
            'bot_signal_direction',
            'Current signal direction (-1=short, 0=neutral, 1=long)',
            ['timeframe']
        )

        # Position metrics
        self.open_positions = Gauge(
            'bot_open_positions',
            'Number of open positions'
        )

        self.position_value = Gauge(
            'bot_position_value',
            'Total position value'
        )

        # API metrics
        self.api_requests_total = Counter(
            'bot_api_requests_total',
            'Total API requests',
            ['endpoint', 'status']
        )

        self.api_latency = Histogram(
            'bot_api_latency_seconds',
            'API request latency',
            ['endpoint']
        )

        # Error metrics
        self.errors_total = Counter(
            'bot_errors_total',
            'Total errors',
            ['type']
        )

        # Circuit breaker
        self.circuit_breaker_active = Gauge(
            'bot_circuit_breaker_active',
            'Circuit breaker status (1=active, 0=inactive)'
        )

        logger.info("Metrics initialized")

    def record_trade(self, direction: str, outcome: str):
        """
        Record a trade

        Args:
            direction: 'long' or 'short'
            outcome: 'win' or 'loss'
        """
        self.trades_total.labels(direction=direction, outcome=outcome).inc()

    def update_pnl(self, realized: float, unrealized: float):
        """
        Update P&L metrics

        Args:
            realized: Realized P&L
            unrealized: Unrealized P&L
        """
        self.trades_pnl.labels(type='realized').set(realized)
        self.trades_pnl.labels(type='unrealized').set(unrealized)

    def update_equity(self, equity: float):
        """
        Update equity metric

        Args:
            equity: Current equity
        """
        self.equity.set(equity)

    def update_margin_level(self, level: float):
        """
        Update margin level

        Args:
            level: Margin level percentage
        """
        self.margin_level.set(level)

    def update_signal(self, timeframe: int, confidence: float, direction: int):
        """
        Update signal metrics

        Args:
            timeframe: Timeframe in minutes
            confidence: Signal confidence (0-100)
            direction: -1 (short), 0 (neutral), 1 (long)
        """
        tf_str = f"{timeframe}m"
        self.signal_confidence.labels(timeframe=tf_str).set(confidence)
        self.signal_direction.labels(timeframe=tf_str).set(direction)

    def update_positions(self, count: int, total_value: float):
        """
        Update position metrics

        Args:
            count: Number of open positions
            total_value: Total position value
        """
        self.open_positions.set(count)
        self.position_value.set(total_value)

    def record_api_request(self, endpoint: str, status: str, latency: float):
        """
        Record API request

        Args:
            endpoint: API endpoint
            status: Request status (success/error)
            latency: Request latency in seconds
        """
        self.api_requests_total.labels(endpoint=endpoint, status=status).inc()
        self.api_latency.labels(endpoint=endpoint).observe(latency)

    def record_error(self, error_type: str):
        """
        Record an error

        Args:
            error_type: Type of error
        """
        self.errors_total.labels(type=error_type).inc()

    def set_circuit_breaker(self, active: bool):
        """
        Set circuit breaker status

        Args:
            active: True if active
        """
        self.circuit_breaker_active.set(1 if active else 0)


def start_metrics_server(port: int = 8000):
    """
    Start Prometheus metrics server

    Args:
        port: Port to listen on
    """
    try:
        start_http_server(port)
        logger.info(f"Metrics server started on port {port}")
    except Exception as e:
        logger.error(f"Failed to start metrics server: {e}")
