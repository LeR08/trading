"""
Circuit Breaker Module
Implémente un disjoncteur pour arrêter le trading en cas de drawdown excessif
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class CircuitBreakerState(Enum):
    """États possibles du circuit breaker"""
    CLOSED = "closed"      # Trading autorisé
    OPEN = "open"          # Trading bloqué
    HALF_OPEN = "half_open"  # Test de reprise


class CircuitBreaker:
    """
    Circuit breaker pour protéger contre les drawdowns excessifs
    """

    def __init__(
        self,
        max_drawdown_pct: float = 0.15,  # 15% max drawdown
        max_daily_loss_pct: float = 0.05,  # 5% max perte journalière
        max_consecutive_losses: int = 5,
        cooldown_minutes: int = 60
    ):
        """
        Initialise le circuit breaker

        Args:
            max_drawdown_pct: Drawdown maximum autorisé (ex: 0.15 = 15%)
            max_daily_loss_pct: Perte journalière maximum (ex: 0.05 = 5%)
            max_consecutive_losses: Nombre max de pertes consécutives
            cooldown_minutes: Minutes avant de tenter une réouverture
        """
        self.max_drawdown_pct = max_drawdown_pct
        self.max_daily_loss_pct = max_daily_loss_pct
        self.max_consecutive_losses = max_consecutive_losses
        self.cooldown_minutes = cooldown_minutes

        # État interne
        self.state = CircuitBreakerState.CLOSED
        self.initial_equity = 0.0
        self.peak_equity = 0.0
        self.daily_start_equity = 0.0
        self.consecutive_losses = 0
        self.last_trip_time: Optional[datetime] = None
        self.last_reset_date = datetime.now().date()

        # Métriques
        self.total_trips = 0
        self.trip_history = []

    def initialize(self, equity: float):
        """
        Initialise le circuit breaker avec l'équité de départ

        Args:
            equity: Équité initiale
        """
        self.initial_equity = equity
        self.peak_equity = equity
        self.daily_start_equity = equity
        logger.info(f"Circuit Breaker initialisé avec équité: {equity:.2f}")

    def check(self, current_equity: float) -> Dict:
        """
        Vérifie l'état du circuit breaker

        Args:
            current_equity: Équité actuelle

        Returns:
            Dict avec:
            {
                'trading_allowed': bool,
                'state': str,
                'reason': str,
                'current_drawdown': float,
                'daily_loss': float,
                'consecutive_losses': int
            }
        """
        # Reset journalier
        self._check_daily_reset()

        # Mettre à jour peak equity
        if current_equity > self.peak_equity:
            self.peak_equity = current_equity

        # Calculer métriques
        drawdown = self._calculate_drawdown(current_equity)
        daily_loss = self._calculate_daily_loss(current_equity)

        # Vérifier si on peut rouvrir le circuit
        if self.state == CircuitBreakerState.OPEN:
            if self._can_attempt_reopen():
                self.state = CircuitBreakerState.HALF_OPEN
                logger.info("Circuit Breaker: passage à HALF_OPEN")

        # Vérifier les conditions de trip
        should_trip, trip_reason = self._should_trip(
            drawdown,
            daily_loss,
            self.consecutive_losses
        )

        if should_trip and self.state != CircuitBreakerState.OPEN:
            self._trip(trip_reason)

        # Déterminer si le trading est autorisé
        trading_allowed = (
            self.state == CircuitBreakerState.CLOSED or
            self.state == CircuitBreakerState.HALF_OPEN
        )

        return {
            'trading_allowed': trading_allowed,
            'state': self.state.value,
            'reason': self._get_state_reason(),
            'current_drawdown': round(drawdown, 4),
            'daily_loss': round(daily_loss, 4),
            'consecutive_losses': self.consecutive_losses,
            'peak_equity': self.peak_equity,
            'initial_equity': self.initial_equity
        }

    def record_trade_result(self, pnl: float, equity_after: float):
        """
        Enregistre le résultat d'un trade

        Args:
            pnl: Profit/Loss du trade
            equity_after: Équité après le trade
        """
        if pnl < 0:
            self.consecutive_losses += 1
            logger.warning(
                f"Perte enregistrée: {pnl:.2f}, "
                f"pertes consécutives: {self.consecutive_losses}"
            )
        else:
            # Reset sur un gain
            if self.consecutive_losses > 0:
                logger.info(
                    f"Gain après {self.consecutive_losses} pertes consécutives"
                )
            self.consecutive_losses = 0

            # Si on était en HALF_OPEN et le trade est profitable, réouvrir
            if self.state == CircuitBreakerState.HALF_OPEN:
                self._reset()
                logger.info("Circuit Breaker: RÉOUVERT après trade profitable")

    def force_reset(self):
        """Force la réouverture du circuit breaker"""
        self._reset()
        logger.warning("Circuit Breaker: RÉOUVERTURE FORCÉE par opérateur")

    def _calculate_drawdown(self, current_equity: float) -> float:
        """
        Calcule le drawdown depuis le peak

        Args:
            current_equity: Équité actuelle

        Returns:
            Drawdown en pourcentage (négatif)
        """
        if self.peak_equity <= 0:
            return 0.0

        drawdown = (current_equity - self.peak_equity) / self.peak_equity

        return drawdown

    def _calculate_daily_loss(self, current_equity: float) -> float:
        """
        Calcule la perte journalière

        Args:
            current_equity: Équité actuelle

        Returns:
            Perte journalière en pourcentage (négatif)
        """
        if self.daily_start_equity <= 0:
            return 0.0

        daily_change = (current_equity - self.daily_start_equity) / self.daily_start_equity

        return daily_change

    def _should_trip(
        self,
        drawdown: float,
        daily_loss: float,
        consecutive_losses: int
    ) -> tuple[bool, str]:
        """
        Détermine si le circuit doit se déclencher

        Args:
            drawdown: Drawdown actuel
            daily_loss: Perte journalière
            consecutive_losses: Nombre de pertes consécutives

        Returns:
            Tuple (should_trip, reason)
        """
        # Drawdown excessif
        if drawdown <= -self.max_drawdown_pct:
            return True, (
                f"Drawdown excessif: {drawdown:.2%} "
                f"(max: {-self.max_drawdown_pct:.2%})"
            )

        # Perte journalière excessive
        if daily_loss <= -self.max_daily_loss_pct:
            return True, (
                f"Perte journalière excessive: {daily_loss:.2%} "
                f"(max: {-self.max_daily_loss_pct:.2%})"
            )

        # Trop de pertes consécutives
        if consecutive_losses >= self.max_consecutive_losses:
            return True, (
                f"Trop de pertes consécutives: {consecutive_losses} "
                f"(max: {self.max_consecutive_losses})"
            )

        return False, ""

    def _trip(self, reason: str):
        """
        Déclenche le circuit breaker

        Args:
            reason: Raison du déclenchement
        """
        self.state = CircuitBreakerState.OPEN
        self.last_trip_time = datetime.now()
        self.total_trips += 1

        trip_event = {
            'time': self.last_trip_time,
            'reason': reason,
            'consecutive_losses': self.consecutive_losses
        }
        self.trip_history.append(trip_event)

        logger.error(f"[RED] CIRCUIT BREAKER DÉCLENCHÉ: {reason}")

    def _reset(self):
        """Réinitialise le circuit breaker"""
        self.state = CircuitBreakerState.CLOSED
        self.consecutive_losses = 0
        logger.info("[GREEN] Circuit Breaker: FERMÉ (trading autorisé)")

    def _can_attempt_reopen(self) -> bool:
        """
        Vérifie si on peut tenter de rouvrir le circuit

        Returns:
            True si cooldown écoulé
        """
        if not self.last_trip_time:
            return True

        elapsed = datetime.now() - self.last_trip_time
        cooldown = timedelta(minutes=self.cooldown_minutes)

        return elapsed >= cooldown

    def _check_daily_reset(self):
        """Vérifie si on doit réinitialiser les métriques journalières"""
        today = datetime.now().date()

        if today != self.last_reset_date:
            logger.info(f"Reset journalier du Circuit Breaker")
            self.last_reset_date = today
            self.consecutive_losses = 0
            # Note: on ne reset pas daily_start_equity ici,
            # il sera mis à jour au premier check de la journée

    def _get_state_reason(self) -> str:
        """
        Retourne la raison de l'état actuel

        Returns:
            Message expliquant l'état
        """
        if self.state == CircuitBreakerState.CLOSED:
            return "Trading autorisé - conditions normales"

        if self.state == CircuitBreakerState.OPEN:
            if self.last_trip_time:
                elapsed = datetime.now() - self.last_trip_time
                remaining = timedelta(minutes=self.cooldown_minutes) - elapsed
                minutes_remaining = max(0, remaining.total_seconds() / 60)
                return (
                    f"Trading bloqué - cooldown restant: {minutes_remaining:.0f}min"
                )
            return "Trading bloqué"

        if self.state == CircuitBreakerState.HALF_OPEN:
            return "Mode test - un trade profitable réouvrira le circuit"

        return "État inconnu"

    def get_statistics(self) -> Dict:
        """
        Retourne les statistiques du circuit breaker

        Returns:
            Dict avec statistiques
        """
        return {
            'total_trips': self.total_trips,
            'current_state': self.state.value,
            'consecutive_losses': self.consecutive_losses,
            'trip_history': self.trip_history[-10:],  # 10 derniers événements
            'peak_equity': self.peak_equity,
            'initial_equity': self.initial_equity
        }
