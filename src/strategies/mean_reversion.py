"""
Mean Reversion Strategy
Stratégie basée sur le retour à la moyenne avec Bollinger Bands et RSI
"""
import pandas as pd
import numpy as np
from typing import Dict
from .base import BaseStrategy


class MeanReversionStrategy(BaseStrategy):
    """
    Stratégie de retour à la moyenne
    Utilise les Bollinger Bands et RSI pour détecter les situations de surachat/survente
    """

    def __init__(
        self,
        bb_period: int = 20,
        bb_std: float = 2.0,
        rsi_period: int = 14,
        rsi_oversold: int = 30,
        rsi_overbought: int = 70,
        tp_pct: float = 0.02,  # 2% take profit
        sl_pct: float = 0.03   # 3% stop loss
    ):
        """
        Initialise la stratégie Mean Reversion

        Args:
            bb_period: Période pour Bollinger Bands
            bb_std: Nombre d'écarts-types pour les bandes
            rsi_period: Période pour RSI
            rsi_oversold: Seuil RSI survente
            rsi_overbought: Seuil RSI surachat
            tp_pct: Pourcentage take profit
            sl_pct: Pourcentage stop loss
        """
        super().__init__("MeanReversion")
        self.bb_period = bb_period
        self.bb_std = bb_std
        self.rsi_period = rsi_period
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
        self.tp_pct = tp_pct
        self.sl_pct = sl_pct

    def calculate_bollinger_bands(self, close: pd.Series) -> Dict[str, pd.Series]:
        """
        Calcule les Bollinger Bands

        Args:
            close: Série de prix de clôture

        Returns:
            Dict avec upper, middle, lower bands
        """
        middle = close.rolling(window=self.bb_period).mean()
        std = close.rolling(window=self.bb_period).std()

        upper = middle + (std * self.bb_std)
        lower = middle - (std * self.bb_std)

        return {
            'upper': upper,
            'middle': middle,
            'lower': lower
        }

    def calculate_bb_position(self, price: float, upper: float, lower: float, middle: float) -> float:
        """
        Calcule la position du prix dans les bandes de Bollinger (0-1)

        Args:
            price: Prix actuel
            upper: Bande supérieure
            lower: Bande inférieure
            middle: Bande moyenne

        Returns:
            Position relative (0 = bande inférieure, 0.5 = moyenne, 1 = bande supérieure)
        """
        if upper == lower:
            return 0.5

        return (price - lower) / (upper - lower)

    def generate_signal(self, market_data: pd.DataFrame) -> Dict:
        """
        Génère un signal basé sur le retour à la moyenne

        Logique:
        - BUY: Prix touche/dépasse bande inférieure + RSI < 30 (survente)
        - SELL: Prix touche/dépasse bande supérieure + RSI > 70 (surachat)
        - HOLD: Prix dans la zone neutre

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

        # Calcul des Bollinger Bands
        bb = self.calculate_bollinger_bands(close)
        upper = bb['upper']
        middle = bb['middle']
        lower = bb['lower']

        # Calcul du RSI
        rsi = self.calculate_rsi(close, self.rsi_period)

        # Valeurs actuelles
        current_price = close.iloc[-1]
        current_upper = upper.iloc[-1]
        current_middle = middle.iloc[-1]
        current_lower = lower.iloc[-1]
        current_rsi = rsi.iloc[-1]

        # Position relative dans les bandes
        bb_position = self.calculate_bb_position(
            current_price,
            current_upper,
            current_lower,
            current_middle
        )

        # Largeur des bandes (volatilité)
        bb_width = (current_upper - current_lower) / current_middle

        # Génération du signal
        side = 'hold'
        confidence = 0.0
        reason = "Prix dans la zone neutre"

        # Signal BUY - Prix bas + RSI survente
        if bb_position < 0.2 and current_rsi < self.rsi_oversold:
            side = 'buy'
            # Confidence basée sur distance à la bande et RSI
            rsi_factor = (self.rsi_oversold - current_rsi) / self.rsi_oversold
            bb_factor = (0.2 - bb_position) / 0.2
            confidence = min(0.5 + (rsi_factor * 0.3) + (bb_factor * 0.2), 1.0)
            reason = f"Survente détectée: Prix={bb_position:.2%} des BB, RSI={current_rsi:.1f}"

        # Signal SELL - Prix haut + RSI surachat
        elif bb_position > 0.8 and current_rsi > self.rsi_overbought:
            side = 'sell'
            rsi_factor = (current_rsi - self.rsi_overbought) / (100 - self.rsi_overbought)
            bb_factor = (bb_position - 0.8) / 0.2
            confidence = min(0.5 + (rsi_factor * 0.3) + (bb_factor * 0.2), 1.0)
            reason = f"Surachat détecté: Prix={bb_position:.2%} des BB, RSI={current_rsi:.1f}"

        # Ajustement de confidence selon volatilité
        # Plus de volatilité = moins de confidence
        if bb_width > 0.1:  # Haute volatilité
            confidence *= 0.8

        # Calcul TP/SL basés sur les bandes et pourcentages
        if side == 'buy':
            # TP vers la moyenne ou bande supérieure
            tp = max(current_middle, current_price * (1 + self.tp_pct))
            sl = current_price * (1 - self.sl_pct)
        elif side == 'sell':
            tp = min(current_middle, current_price * (1 - self.tp_pct))
            sl = current_price * (1 + self.sl_pct)
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
