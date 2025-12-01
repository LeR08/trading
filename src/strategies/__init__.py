"""
Strategies Module
Contient toutes les stratégies de trading disponibles
"""
from .base import BaseStrategy
from .trend_following import TrendFollowingStrategy
from .mean_reversion import MeanReversionStrategy
from .breakout import BreakoutStrategy

__all__ = [
    'BaseStrategy',
    'TrendFollowingStrategy',
    'MeanReversionStrategy',
    'BreakoutStrategy'
]
