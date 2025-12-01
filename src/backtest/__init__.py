"""
Backtest Module
Moteur de backtesting avec simulation réaliste (slippage, fees)
"""
from .engine import BacktestEngine, PositionSide

__all__ = [
    'BacktestEngine',
    'PositionSide'
]
