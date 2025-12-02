"""
Backtest Engine - Simulates trading strategy on historical data

Features:
- Candle-by-candle simulation
- Slippage and fee modeling
- Performance metrics calculation
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


@dataclass
class BacktestTrade:
    """Represents a trade in backtest"""
    entry_time: datetime
    entry_price: float
    direction: str  # 'long' or 'short'
    volume: float
    stop_loss: float
    take_profit: float
    exit_time: Optional[datetime] = None
    exit_price: Optional[float] = None
    exit_reason: Optional[str] = None  # 'sl', 'tp', 'timeout', 'signal'
    pnl: float = 0.0
    pnl_pct: float = 0.0
    fees: float = 0.0
    slippage: float = 0.0


@dataclass
class BacktestMetrics:
    """Backtest performance metrics"""
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0

    total_pnl: float = 0.0
    total_return_pct: float = 0.0

    avg_win: float = 0.0
    avg_loss: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0

    profit_factor: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_pct: float = 0.0

    total_fees: float = 0.0
    total_slippage: float = 0.0

    equity_curve: List[float] = field(default_factory=list)
    equity_timestamps: List[datetime] = field(default_factory=list)


class BacktestEngine:
    """
    Backtesting engine for strategy validation

    Simulates:
    - Entry/exit execution
    - Slippage
    - Trading fees
    - Position management
    """

    def __init__(
        self,
        initial_equity: float = 10000.0,
        maker_fee: float = 0.0016,  # 0.16% Kraken maker fee
        taker_fee: float = 0.0026,  # 0.26% Kraken taker fee
        slippage_pct: float = 0.001,  # 0.1% slippage
        leverage: int = 3,
    ):
        """
        Initialize backtest engine

        Args:
            initial_equity: Starting equity
            maker_fee: Maker fee percentage
            taker_fee: Taker fee percentage
            slippage_pct: Slippage percentage
            leverage: Trading leverage
        """
        self.initial_equity = initial_equity
        self.maker_fee = maker_fee
        self.taker_fee = taker_fee
        self.slippage_pct = slippage_pct
        self.leverage = leverage

        # State
        self.equity = initial_equity
        self.trades: List[BacktestTrade] = []
        self.open_trades: List[BacktestTrade] = []
        self.equity_curve = [initial_equity]
        self.equity_timestamps = []

    def _calculate_slippage(self, price: float, direction: str) -> float:
        """
        Calculate slippage

        Args:
            price: Base price
            direction: 'long' or 'short'

        Returns:
            Slippage adjusted price
        """
        if direction == "long":
            return price * (1 + self.slippage_pct)
        else:
            return price * (1 - self.slippage_pct)

    def _calculate_fees(self, notional_value: float, is_maker: bool = False) -> float:
        """
        Calculate trading fees

        Args:
            notional_value: Notional value of trade
            is_maker: Whether it's a maker order

        Returns:
            Fee amount
        """
        fee_rate = self.maker_fee if is_maker else self.taker_fee
        return notional_value * fee_rate

    def open_position(
        self,
        timestamp: datetime,
        price: float,
        direction: str,
        volume: float,
        stop_loss: float,
        take_profit: float,
        is_limit: bool = False
    ) -> bool:
        """
        Open a position

        Args:
            timestamp: Entry timestamp
            price: Entry price
            direction: 'long' or 'short'
            volume: Position volume
            stop_loss: Stop loss price
            take_profit: Take profit price
            is_limit: Whether it's a limit order

        Returns:
            True if position opened successfully
        """
        # Apply slippage
        if not is_limit:
            entry_price = self._calculate_slippage(price, direction)
        else:
            entry_price = price

        # Calculate notional value
        notional_value = volume * entry_price

        # Calculate required margin
        required_margin = notional_value / self.leverage

        # Check if enough equity
        if required_margin > self.equity * 0.8:  # Max 80% of equity per trade
            logger.warning(f"Insufficient equity for trade: required=${required_margin:.2f}, available=${self.equity:.2f}")
            return False

        # Calculate fees
        fees = self._calculate_fees(notional_value, is_maker=is_limit)

        # Create trade
        trade = BacktestTrade(
            entry_time=timestamp,
            entry_price=entry_price,
            direction=direction,
            volume=volume,
            stop_loss=stop_loss,
            take_profit=take_profit,
            fees=fees,
            slippage=abs(entry_price - price) * volume
        )

        self.open_trades.append(trade)
        self.equity -= fees  # Deduct entry fees

        logger.debug(f"Position opened: {direction} {volume:.8f} @ ${entry_price:.2f}")

        return True

    def check_exits(self, timestamp: datetime, high: float, low: float, close: float):
        """
        Check if any open positions should be closed

        Args:
            timestamp: Current timestamp
            high: Candle high
            low: Candle low
            close: Candle close
        """
        closed_trades = []

        for trade in self.open_trades:
            exit_price = None
            exit_reason = None

            # Check SL/TP
            if trade.direction == "long":
                if low <= trade.stop_loss:
                    exit_price = trade.stop_loss
                    exit_reason = "sl"
                elif high >= trade.take_profit:
                    exit_price = trade.take_profit
                    exit_reason = "tp"
            else:  # short
                if high >= trade.stop_loss:
                    exit_price = trade.stop_loss
                    exit_reason = "sl"
                elif low <= trade.take_profit:
                    exit_price = trade.take_profit
                    exit_reason = "tp"

            # If hit SL/TP, close position
            if exit_price:
                self._close_position(trade, timestamp, exit_price, exit_reason)
                closed_trades.append(trade)

        # Remove closed trades
        for trade in closed_trades:
            self.open_trades.remove(trade)

    def _close_position(
        self,
        trade: BacktestTrade,
        timestamp: datetime,
        price: float,
        reason: str
    ):
        """
        Close a position

        Args:
            trade: Trade to close
            timestamp: Exit timestamp
            price: Exit price
            reason: Exit reason
        """
        # Apply slippage on exit
        exit_price = self._calculate_slippage(price, "short" if trade.direction == "long" else "long")

        # Calculate P&L
        if trade.direction == "long":
            pnl = (exit_price - trade.entry_price) * trade.volume
        else:
            pnl = (trade.entry_price - exit_price) * trade.volume

        # Account for leverage
        pnl = pnl * self.leverage

        # Calculate exit fees
        notional_value = trade.volume * exit_price
        exit_fees = self._calculate_fees(notional_value, is_maker=False)

        # Total P&L after fees
        total_pnl = pnl - trade.fees - exit_fees

        # Update trade
        trade.exit_time = timestamp
        trade.exit_price = exit_price
        trade.exit_reason = reason
        trade.pnl = total_pnl
        trade.pnl_pct = (total_pnl / (trade.volume * trade.entry_price)) * 100
        trade.fees += exit_fees
        trade.slippage += abs(exit_price - price) * trade.volume

        # Update equity
        self.equity += total_pnl

        # Record equity
        self.equity_curve.append(self.equity)
        self.equity_timestamps.append(timestamp)

        # Store closed trade
        self.trades.append(trade)

        logger.debug(
            f"Position closed: {trade.direction} @ ${exit_price:.2f} | "
            f"P&L: ${total_pnl:.2f} ({trade.pnl_pct:.2f}%) | "
            f"Reason: {reason}"
        )

    def close_all_positions(self, timestamp: datetime, price: float):
        """
        Close all open positions (end of backtest)

        Args:
            timestamp: Exit timestamp
            price: Exit price
        """
        for trade in self.open_trades[:]:
            self._close_position(trade, timestamp, price, "end_of_backtest")
            self.open_trades.remove(trade)

    def calculate_metrics(self) -> BacktestMetrics:
        """
        Calculate backtest performance metrics

        Returns:
            BacktestMetrics
        """
        metrics = BacktestMetrics()

        if not self.trades:
            return metrics

        metrics.total_trades = len(self.trades)

        # Win/Loss stats
        winning_trades = [t for t in self.trades if t.pnl > 0]
        losing_trades = [t for t in self.trades if t.pnl < 0]

        metrics.winning_trades = len(winning_trades)
        metrics.losing_trades = len(losing_trades)
        metrics.win_rate = metrics.winning_trades / metrics.total_trades if metrics.total_trades > 0 else 0

        # P&L stats
        metrics.total_pnl = sum(t.pnl for t in self.trades)
        metrics.total_return_pct = (metrics.total_pnl / self.initial_equity) * 100

        if winning_trades:
            wins = [t.pnl for t in winning_trades]
            metrics.avg_win = np.mean(wins)
            metrics.largest_win = max(wins)

        if losing_trades:
            losses = [t.pnl for t in losing_trades]
            metrics.avg_loss = np.mean(losses)
            metrics.largest_loss = min(losses)

        # Profit factor
        gross_profit = sum(t.pnl for t in winning_trades) if winning_trades else 0
        gross_loss = abs(sum(t.pnl for t in losing_trades)) if losing_trades else 0
        metrics.profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0

        # Sharpe ratio (simplified)
        if len(self.trades) > 1:
            returns = [t.pnl / self.initial_equity for t in self.trades]
            metrics.sharpe_ratio = np.mean(returns) / np.std(returns) if np.std(returns) > 0 else 0
            metrics.sharpe_ratio *= np.sqrt(252)  # Annualized

        # Max drawdown
        if self.equity_curve:
            equity_array = np.array(self.equity_curve)
            running_max = np.maximum.accumulate(equity_array)
            drawdown = equity_array - running_max
            metrics.max_drawdown = abs(drawdown.min())
            metrics.max_drawdown_pct = (metrics.max_drawdown / running_max[drawdown.argmin()]) * 100 if len(running_max) > 0 else 0

        # Fees and slippage
        metrics.total_fees = sum(t.fees for t in self.trades)
        metrics.total_slippage = sum(t.slippage for t in self.trades)

        # Equity curve
        metrics.equity_curve = self.equity_curve
        metrics.equity_timestamps = self.equity_timestamps

        return metrics

    def get_trades_df(self) -> pd.DataFrame:
        """
        Get trades as DataFrame

        Returns:
            DataFrame with trade history
        """
        if not self.trades:
            return pd.DataFrame()

        trades_data = []
        for trade in self.trades:
            trades_data.append({
                'entry_time': trade.entry_time,
                'exit_time': trade.exit_time,
                'direction': trade.direction,
                'entry_price': trade.entry_price,
                'exit_price': trade.exit_price,
                'volume': trade.volume,
                'pnl': trade.pnl,
                'pnl_pct': trade.pnl_pct,
                'exit_reason': trade.exit_reason,
                'fees': trade.fees,
                'slippage': trade.slippage,
            })

        return pd.DataFrame(trades_data)

    def print_summary(self):
        """Print backtest summary"""
        metrics = self.calculate_metrics()

        print("\n" + "=" * 60)
        print("BACKTEST SUMMARY")
        print("=" * 60)
        print(f"Initial Equity:     ${self.initial_equity:,.2f}")
        print(f"Final Equity:       ${self.equity:,.2f}")
        print(f"Total P&L:          ${metrics.total_pnl:,.2f} ({metrics.total_return_pct:.2f}%)")
        print("-" * 60)
        print(f"Total Trades:       {metrics.total_trades}")
        print(f"Winning Trades:     {metrics.winning_trades}")
        print(f"Losing Trades:      {metrics.losing_trades}")
        print(f"Win Rate:           {metrics.win_rate*100:.2f}%")
        print("-" * 60)
        print(f"Avg Win:            ${metrics.avg_win:.2f}")
        print(f"Avg Loss:           ${metrics.avg_loss:.2f}")
        print(f"Largest Win:        ${metrics.largest_win:.2f}")
        print(f"Largest Loss:       ${metrics.largest_loss:.2f}")
        print(f"Profit Factor:      {metrics.profit_factor:.2f}")
        print("-" * 60)
        print(f"Max Drawdown:       ${metrics.max_drawdown:.2f} ({metrics.max_drawdown_pct:.2f}%)")
        print(f"Sharpe Ratio:       {metrics.sharpe_ratio:.2f}")
        print("-" * 60)
        print(f"Total Fees:         ${metrics.total_fees:.2f}")
        print(f"Total Slippage:     ${metrics.total_slippage:.2f}")
        print("=" * 60 + "\n")
