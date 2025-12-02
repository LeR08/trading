"""
Risk Management Engine - Position sizing and risk checks

Handles:
- Position sizing with leverage
- Margin requirement calculations
- Circuit breakers
- Exposure limits
"""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, List
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class RiskCheckStatus(Enum):
    """Risk check result status"""
    APPROVED = "approved"
    REJECTED = "rejected"
    WARNING = "warning"


@dataclass
class RiskCheckResult:
    """Result of risk check"""
    status: RiskCheckStatus
    approved: bool
    reason: Optional[str] = None
    warnings: List[str] = None
    metadata: Dict[str, any] = None


@dataclass
class PositionSize:
    """Calculated position size"""
    volume: float  # In base currency (BTC)
    notional_value: float  # In quote currency (USD)
    margin_required: float  # Margin required for position
    stop_loss_price: float  # Calculated SL price
    take_profit_price: float  # Calculated TP price
    risk_amount: float  # Amount at risk (in quote currency)
    reward_amount: float  # Potential reward
    risk_reward_ratio: float  # R:R ratio


class RiskManager:
    """
    Manages risk for trading operations

    Key parameters:
    - risk_per_trade: % of equity to risk per trade (default: 1%)
    - max_total_exposure: Max % of equity in open positions (default: 5%)
    - leverage: Trading leverage (default: 3)
    - max_daily_drawdown: Max daily loss % before circuit breaker (default: 3%)
    - max_total_drawdown: Max total loss % before halt (default: 10%)
    """

    def __init__(
        self,
        risk_per_trade: float = 0.01,
        max_total_exposure: float = 0.05,
        leverage: int = 3,
        max_daily_drawdown: float = 0.03,
        max_total_drawdown: float = 0.10,
        max_concurrent_trades: int = 3,
    ):
        """
        Initialize risk manager

        Args:
            risk_per_trade: Risk per trade as decimal (0.01 = 1%)
            max_total_exposure: Max total exposure as decimal (0.05 = 5%)
            leverage: Leverage multiplier
            max_daily_drawdown: Max daily drawdown as decimal (0.03 = 3%)
            max_total_drawdown: Max total drawdown as decimal (0.10 = 10%)
            max_concurrent_trades: Maximum concurrent open positions
        """
        self.risk_per_trade = risk_per_trade
        self.max_total_exposure = max_total_exposure
        self.leverage = leverage
        self.max_daily_drawdown = max_daily_drawdown
        self.max_total_drawdown = max_total_drawdown
        self.max_concurrent_trades = max_concurrent_trades

        # Circuit breaker state
        self.circuit_breaker_active = False
        self.circuit_breaker_reason = None

        # Performance tracking
        self.daily_pnl = 0.0
        self.total_pnl = 0.0
        self.starting_equity = 0.0
        self.daily_reset_time = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

        logger.info(f"RiskManager initialized with leverage={leverage}x, risk_per_trade={risk_per_trade*100}%")

    def calculate_position_size(
        self,
        equity: float,
        entry_price: float,
        stop_loss_price: float,
        take_profit_price: float,
        direction: str,  # 'long' or 'short'
        pair_decimals: int = 8,  # BTC has 8 decimals
    ) -> PositionSize:
        """
        Calculate position size based on risk parameters

        IMPORTANT: Uses TradeBalance equity and accounts for leverage

        Args:
            equity: Current account equity (from TradeBalance)
            entry_price: Entry price
            stop_loss_price: Stop loss price
            take_profit_price: Take profit price
            direction: 'long' or 'short'
            pair_decimals: Decimal precision for pair

        Returns:
            PositionSize with calculated values
        """
        # Calculate risk per unit
        if direction == "long":
            risk_per_unit = abs(entry_price - stop_loss_price)
            reward_per_unit = abs(take_profit_price - entry_price)
        else:  # short
            risk_per_unit = abs(stop_loss_price - entry_price)
            reward_per_unit = abs(entry_price - take_profit_price)

        if risk_per_unit <= 0:
            logger.error(f"Invalid risk_per_unit: {risk_per_unit}")
            risk_per_unit = entry_price * 0.01  # Fallback: 1% of price

        # Amount to risk in quote currency (USD)
        risk_amount = equity * self.risk_per_trade

        # Calculate position size in base currency (BTC)
        # volume = risk_amount / risk_per_unit
        volume = risk_amount / risk_per_unit

        # Apply precision
        volume = round(volume, pair_decimals)

        # Calculate notional value
        notional_value = volume * entry_price

        # Calculate margin required (with leverage)
        # Margin = Notional Value / Leverage
        margin_required = notional_value / self.leverage

        # Calculate reward
        reward_amount = volume * reward_per_unit

        # Calculate R:R ratio
        risk_reward_ratio = reward_amount / risk_amount if risk_amount > 0 else 0

        position = PositionSize(
            volume=volume,
            notional_value=notional_value,
            margin_required=margin_required,
            stop_loss_price=stop_loss_price,
            take_profit_price=take_profit_price,
            risk_amount=risk_amount,
            reward_amount=reward_amount,
            risk_reward_ratio=risk_reward_ratio
        )

        logger.info(
            f"Position size calculated: {volume:.8f} BTC @ ${entry_price:.2f} | "
            f"Notional: ${notional_value:.2f} | Margin: ${margin_required:.2f} | R:R: {risk_reward_ratio:.2f}"
        )

        return position

    def check_margin_availability(
        self,
        trade_balance: Dict[str, float],
        required_margin: float
    ) -> RiskCheckResult:
        """
        Check if sufficient margin is available

        IMPORTANT: Uses TradeBalance response from Kraken API
        TradeBalance fields:
        - eb: Equivalent balance
        - tb: Trade balance
        - m: Margin amount of open positions
        - n: Unrealized net P&L
        - c: Cost basis of open positions
        - v: Current floating valuation
        - e: Equity = tb + n
        - mf: Free margin = e - m

        Args:
            trade_balance: TradeBalance dict from Kraken
            required_margin: Required margin for new position

        Returns:
            RiskCheckResult
        """
        try:
            equity = float(trade_balance.get("e", 0))  # Equity
            free_margin = float(trade_balance.get("mf", 0))  # Free margin
            used_margin = float(trade_balance.get("m", 0))  # Used margin

            if free_margin < required_margin:
                return RiskCheckResult(
                    status=RiskCheckStatus.REJECTED,
                    approved=False,
                    reason=f"Insufficient margin: required=${required_margin:.2f}, available=${free_margin:.2f}",
                    metadata={"equity": equity, "free_margin": free_margin, "required": required_margin}
                )

            # Check margin utilization
            total_margin_after = used_margin + required_margin
            margin_utilization = total_margin_after / equity if equity > 0 else 1.0

            warnings = []
            if margin_utilization > 0.8:
                warnings.append(f"High margin utilization: {margin_utilization*100:.1f}%")

            return RiskCheckResult(
                status=RiskCheckStatus.APPROVED,
                approved=True,
                warnings=warnings,
                metadata={
                    "equity": equity,
                    "free_margin": free_margin,
                    "used_margin": used_margin,
                    "margin_utilization": margin_utilization
                }
            )

        except Exception as e:
            logger.error(f"Error checking margin: {e}", exc_info=True)
            return RiskCheckResult(
                status=RiskCheckStatus.REJECTED,
                approved=False,
                reason=f"Error checking margin: {str(e)}"
            )

    def check_exposure_limit(
        self,
        current_exposure: float,
        new_position_value: float,
        equity: float
    ) -> RiskCheckResult:
        """
        Check if new position would exceed exposure limits

        Args:
            current_exposure: Current total position value
            new_position_value: Value of new position
            equity: Current equity

        Returns:
            RiskCheckResult
        """
        total_exposure = current_exposure + new_position_value
        exposure_ratio = total_exposure / equity if equity > 0 else 1.0

        if exposure_ratio > self.max_total_exposure:
            return RiskCheckResult(
                status=RiskCheckStatus.REJECTED,
                approved=False,
                reason=f"Exposure limit exceeded: {exposure_ratio*100:.1f}% > {self.max_total_exposure*100:.1f}%",
                metadata={"total_exposure": total_exposure, "equity": equity, "ratio": exposure_ratio}
            )

        warnings = []
        if exposure_ratio > self.max_total_exposure * 0.8:
            warnings.append(f"Approaching exposure limit: {exposure_ratio*100:.1f}%")

        return RiskCheckResult(
            status=RiskCheckStatus.APPROVED,
            approved=True,
            warnings=warnings,
            metadata={"total_exposure": total_exposure, "equity": equity, "ratio": exposure_ratio}
        )

    def check_concurrent_trades(self, current_trades: int) -> RiskCheckResult:
        """
        Check if max concurrent trades limit is reached

        Args:
            current_trades: Number of current open trades

        Returns:
            RiskCheckResult
        """
        if current_trades >= self.max_concurrent_trades:
            return RiskCheckResult(
                status=RiskCheckStatus.REJECTED,
                approved=False,
                reason=f"Max concurrent trades reached: {current_trades}/{self.max_concurrent_trades}",
                metadata={"current_trades": current_trades, "max_trades": self.max_concurrent_trades}
            )

        return RiskCheckResult(
            status=RiskCheckStatus.APPROVED,
            approved=True,
            metadata={"current_trades": current_trades, "max_trades": self.max_concurrent_trades}
        )

    def check_circuit_breaker(self) -> RiskCheckResult:
        """
        Check circuit breaker status

        Returns:
            RiskCheckResult
        """
        if self.circuit_breaker_active:
            return RiskCheckResult(
                status=RiskCheckStatus.REJECTED,
                approved=False,
                reason=f"Circuit breaker active: {self.circuit_breaker_reason}",
                metadata={"reason": self.circuit_breaker_reason}
            )

        return RiskCheckResult(
            status=RiskCheckStatus.APPROVED,
            approved=True
        )

    def update_pnl(self, pnl: float, equity: float):
        """
        Update P&L tracking and check drawdown limits

        Args:
            pnl: Realized P&L from trade
            equity: Current equity
        """
        # Reset daily P&L at midnight UTC
        now = datetime.now(timezone.utc)
        if now >= self.daily_reset_time + timedelta(days=1):
            self.daily_pnl = 0.0
            self.daily_reset_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
            logger.info("Daily P&L reset")

        self.daily_pnl += pnl
        self.total_pnl += pnl

        # Update starting equity if not set
        if self.starting_equity == 0:
            self.starting_equity = equity

        # Check daily drawdown
        daily_drawdown = abs(self.daily_pnl / equity) if equity > 0 else 0
        if self.daily_pnl < 0 and daily_drawdown > self.max_daily_drawdown:
            self.activate_circuit_breaker(f"Daily drawdown limit exceeded: {daily_drawdown*100:.2f}%")

        # Check total drawdown
        total_drawdown = abs((equity - self.starting_equity) / self.starting_equity) if self.starting_equity > 0 else 0
        if equity < self.starting_equity and total_drawdown > self.max_total_drawdown:
            self.activate_circuit_breaker(f"Total drawdown limit exceeded: {total_drawdown*100:.2f}%")

        logger.info(f"P&L updated: Daily=${self.daily_pnl:.2f}, Total=${self.total_pnl:.2f}")

    def activate_circuit_breaker(self, reason: str):
        """
        Activate circuit breaker to halt trading

        Args:
            reason: Reason for activation
        """
        self.circuit_breaker_active = True
        self.circuit_breaker_reason = reason
        logger.critical(f"CIRCUIT BREAKER ACTIVATED: {reason}")

    def deactivate_circuit_breaker(self):
        """Deactivate circuit breaker (manual intervention required)"""
        self.circuit_breaker_active = False
        self.circuit_breaker_reason = None
        logger.warning("Circuit breaker deactivated")

    def perform_full_risk_check(
        self,
        position_size: PositionSize,
        trade_balance: Dict[str, float],
        current_open_positions: List[Dict],
    ) -> RiskCheckResult:
        """
        Perform comprehensive risk check before opening position

        Args:
            position_size: Calculated position size
            trade_balance: Current trade balance from Kraken
            current_open_positions: List of current open positions

        Returns:
            RiskCheckResult with approval/rejection
        """
        logger.info("Performing full risk check")

        all_warnings = []

        # 1. Circuit breaker check
        cb_check = self.check_circuit_breaker()
        if not cb_check.approved:
            return cb_check

        # 2. Margin check
        margin_check = self.check_margin_availability(trade_balance, position_size.margin_required)
        if not margin_check.approved:
            return margin_check
        if margin_check.warnings:
            all_warnings.extend(margin_check.warnings)

        # 3. Concurrent trades check
        trades_check = self.check_concurrent_trades(len(current_open_positions))
        if not trades_check.approved:
            return trades_check

        # 4. Exposure check
        equity = float(trade_balance.get("e", 0))
        current_exposure = sum(float(pos.get("value", 0)) for pos in current_open_positions)
        exposure_check = self.check_exposure_limit(current_exposure, position_size.notional_value, equity)
        if not exposure_check.approved:
            return exposure_check
        if exposure_check.warnings:
            all_warnings.extend(exposure_check.warnings)

        # All checks passed
        logger.info("All risk checks passed")
        return RiskCheckResult(
            status=RiskCheckStatus.APPROVED,
            approved=True,
            warnings=all_warnings if all_warnings else None,
            metadata={
                "margin_required": position_size.margin_required,
                "equity": equity,
                "open_positions": len(current_open_positions),
                "exposure_ratio": (current_exposure + position_size.notional_value) / equity if equity > 0 else 0
            }
        )

    def calculate_stop_loss(
        self,
        entry_price: float,
        atr: float,
        direction: str,
        atr_multiplier: float = 1.0
    ) -> float:
        """
        Calculate stop loss price based on ATR

        Args:
            entry_price: Entry price
            atr: Current ATR value
            direction: 'long' or 'short'
            atr_multiplier: ATR multiplier (default: 1.0)

        Returns:
            Stop loss price
        """
        sl_distance = atr * atr_multiplier

        if direction == "long":
            sl_price = entry_price - sl_distance
        else:  # short
            sl_price = entry_price + sl_distance

        return sl_price

    def calculate_take_profit(
        self,
        entry_price: float,
        stop_loss_price: float,
        direction: str,
        reward_ratio: float = 0.7
    ) -> float:
        """
        Calculate take profit price based on risk-reward ratio

        Args:
            entry_price: Entry price
            stop_loss_price: Stop loss price
            direction: 'long' or 'short'
            reward_ratio: Reward multiplier (default: 0.7 for scalping)

        Returns:
            Take profit price
        """
        risk_distance = abs(entry_price - stop_loss_price)
        reward_distance = risk_distance * reward_ratio

        if direction == "long":
            tp_price = entry_price + reward_distance
        else:  # short
            tp_price = entry_price - reward_distance

        return tp_price
