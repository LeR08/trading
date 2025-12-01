"""
Trend Following Strategy
Stratégie basée sur le suivi de tendance avec EMAs et MACD
"""
import pandas as pd
import numpy as np
from typing import Dict
from .base import BaseStrategy


class TrendFollowingStrategy(BaseStrategy):
    """
    Stratégie de suivi de tendance
    Utilise les EMAs (9, 21, 50) et MACD pour identifier les tendances
    """

    def __init__(
        self,
        ema_fast: int = 9,
        ema_medium: int = 21,
        ema_slow: int = 50,
        macd_fast: int = 12,
        macd_slow: int = 26,
        macd_signal: int = 9,
        tp_multiplier: float = 2.0,
        sl_multiplier: float = 1.5
    ):
        """
        Initialise la stratégie Trend Following

        Args:
            ema_fast: Période EMA rapide
            ema_medium: Période EMA moyenne
            ema_slow: Période EMA lente
            macd_fast: Période MACD rapide
            macd_slow: Période MACD lente
            macd_signal: Période ligne de signal MACD
            tp_multiplier: Multiplicateur ATR pour take profit
            sl_multiplier: Multiplicateur ATR pour stop loss
        """
        super().__init__("TrendFollowing")
        self.ema_fast = ema_fast
        self.ema_medium = ema_medium
        self.ema_slow = ema_slow
        self.macd_fast = macd_fast
        self.macd_slow = macd_slow
        self.macd_signal = macd_signal
        self.tp_multiplier = tp_multiplier
        self.sl_multiplier = sl_multiplier

    def calculate_macd(self, close: pd.Series) -> Dict[str, pd.Series]:
        """
        Calcule le MACD

        Args:
            close: Série de prix de clôture

        Returns:
            Dict avec macd, signal, histogram
        """
        ema_fast = self.calculate_ema(close, self.macd_fast)
        ema_slow = self.calculate_ema(close, self.macd_slow)

        macd = ema_fast - ema_slow
        signal = macd.ewm(span=self.macd_signal, adjust=False).mean()
        histogram = macd - signal

        return {
            'macd': macd,
            'signal': signal,
            'histogram': histogram
        }

    def generate_signal(self, market_data: pd.DataFrame) -> Dict:
        """
        Génère un signal basé sur la tendance

        Logique:
        - BUY: EMA rapide > EMA moyenne > EMA lente + MACD crossover haussier
        - SELL: EMA rapide < EMA moyenne < EMA lente + MACD crossover baissier
        - HOLD: Pas de tendance claire

        Args:
            market_data: DataFrame OHLCV

        Returns:
            Dict avec signal
        """
        if not self.validate_market_data(market_data):
            return {
                'side': 'hold',
                'confidence': 0.0,
                'price': 0.0,
                'tp': 0.0,
                'sl': 0.0,
                'reason': 'Données de marché invalides'
            }

        close = market_data['close']

        # Calcul des EMAs
        ema_fast = self.calculate_ema(close, self.ema_fast)
        ema_medium = self.calculate_ema(close, self.ema_medium)
        ema_slow = self.calculate_ema(close, self.ema_slow)

        # Calcul du MACD
        macd_data = self.calculate_macd(close)
        macd = macd_data['macd']
        signal_line = macd_data['signal']
        histogram = macd_data['histogram']

        # Valeurs actuelles
        current_price = close.iloc[-1]
        current_ema_fast = ema_fast.iloc[-1]
        current_ema_medium = ema_medium.iloc[-1]
        current_ema_slow = ema_slow.iloc[-1]
        current_macd = macd.iloc[-1]
        current_signal = signal_line.iloc[-1]
        current_histogram = histogram.iloc[-1]
        prev_histogram = histogram.iloc[-2]

        # ATR pour TP/SL
        atr = self.calculate_atr(market_data)

        # Détection de la tendance
        bullish_trend = (
            current_ema_fast > current_ema_medium > current_ema_slow
        )
        bearish_trend = (
            current_ema_fast < current_ema_medium < current_ema_slow
        )

        # Détection du crossover MACD
        bullish_crossover = (current_histogram > 0 and prev_histogram <= 0)
        bearish_crossover = (current_histogram < 0 and prev_histogram >= 0)

        # Force du signal MACD
        macd_strength = abs(current_macd - current_signal)

        # Génération du signal
        side = 'hold'
        confidence = 0.0
        reason = "Pas de tendance claire"

        # Signal BUY
        if bullish_trend and (bullish_crossover or current_macd > current_signal):
            side = 'buy'
            # Confidence basée sur alignement EMAs et force MACD
            ema_alignment = (current_ema_fast - current_ema_slow) / current_price
            confidence = min(0.5 + (ema_alignment * 100) + (macd_strength * 0.1), 1.0)
            reason = f"Tendance haussière confirmée: EMA alignment + MACD bullish"

        # Signal SELL
        elif bearish_trend and (bearish_crossover or current_macd < current_signal):
            side = 'sell'
            ema_alignment = (current_ema_slow - current_ema_fast) / current_price
            confidence = min(0.5 + (ema_alignment * 100) + (macd_strength * 0.1), 1.0)
            reason = f"Tendance baissière confirmée: EMA alignment + MACD bearish"

        # Calcul TP/SL basés sur ATR
        if side == 'buy':
            tp = current_price + (atr * self.tp_multiplier)
            sl = current_price - (atr * self.sl_multiplier)
        elif side == 'sell':
            tp = current_price - (atr * self.tp_multiplier)
            sl = current_price + (atr * self.sl_multiplier)
        else:
            tp = current_price
            sl = current_price

        return {
            'side': side,
            'confidence': round(confidence, 3),
            'price': round(current_price, 2),
            'tp': round(tp, 2),
            'sl': round(sl, 2),
            'reason': reason
        }
