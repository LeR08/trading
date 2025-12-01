"""
Breakout Strategy
Stratégie basée sur les cassures de niveaux de support/résistance avec confirmation de volume
"""
import pandas as pd
import numpy as np
from typing import Dict, Tuple
from .base import BaseStrategy


class BreakoutStrategy(BaseStrategy):
    """
    Stratégie de cassure (breakout)
    Identifie les niveaux de support/résistance et détecte les cassures
    avec confirmation par le volume
    """

    def __init__(
        self,
        lookback_period: int = 50,
        volume_ma_period: int = 20,
        volume_multiplier: float = 1.5,
        breakout_threshold: float = 0.002,  # 0.2% de mouvement minimum
        tp_multiplier: float = 2.5,
        sl_multiplier: float = 1.0
    ):
        """
        Initialise la stratégie Breakout

        Args:
            lookback_period: Période pour identifier les niveaux S/R
            volume_ma_period: Période pour moyenne mobile du volume
            volume_multiplier: Multiplicateur pour confirmer volume élevé
            breakout_threshold: Seuil minimum de cassure (en %)
            tp_multiplier: Multiplicateur ATR pour take profit
            sl_multiplier: Multiplicateur ATR pour stop loss
        """
        super().__init__("Breakout")
        self.lookback_period = lookback_period
        self.volume_ma_period = volume_ma_period
        self.volume_multiplier = volume_multiplier
        self.breakout_threshold = breakout_threshold
        self.tp_multiplier = tp_multiplier
        self.sl_multiplier = sl_multiplier

    def find_support_resistance(
        self,
        market_data: pd.DataFrame,
        lookback: int
    ) -> Tuple[float, float]:
        """
        Identifie les niveaux de support et résistance

        Args:
            market_data: DataFrame OHLCV
            lookback: Nombre de périodes à regarder

        Returns:
            Tuple (support_level, resistance_level)
        """
        recent_data = market_data.tail(lookback)

        # Résistance = plus haut récent
        resistance = recent_data['high'].max()

        # Support = plus bas récent
        support = recent_data['low'].min()

        return support, resistance

    def is_breakout(
        self,
        current_price: float,
        level: float,
        direction: str
    ) -> bool:
        """
        Détermine si il y a cassure d'un niveau

        Args:
            current_price: Prix actuel
            level: Niveau à casser
            direction: 'up' ou 'down'

        Returns:
            True si cassure détectée
        """
        price_diff = abs(current_price - level) / level

        if direction == 'up':
            return current_price > level and price_diff >= self.breakout_threshold
        else:  # down
            return current_price < level and price_diff >= self.breakout_threshold

    def calculate_volume_confirmation(
        self,
        market_data: pd.DataFrame
    ) -> Tuple[bool, float]:
        """
        Vérifie si le volume confirme le mouvement

        Args:
            market_data: DataFrame OHLCV

        Returns:
            Tuple (is_high_volume, volume_ratio)
        """
        volume = market_data['volume']

        # Moyenne mobile du volume
        volume_ma = volume.rolling(window=self.volume_ma_period).mean()

        current_volume = volume.iloc[-1]
        avg_volume = volume_ma.iloc[-1]

        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 0

        is_high_volume = volume_ratio >= self.volume_multiplier

        return is_high_volume, volume_ratio

    def generate_signal(self, market_data: pd.DataFrame) -> Dict:
        """
        Génère un signal basé sur les cassures

        Logique:
        - BUY: Prix casse la résistance + volume élevé
        - SELL: Prix casse le support + volume élevé
        - HOLD: Pas de cassure ou volume insuffisant

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
        current_price = close.iloc[-1]

        # Identifier les niveaux S/R
        support, resistance = self.find_support_resistance(
            market_data,
            self.lookback_period
        )

        # Vérifier la confirmation par volume
        high_volume, volume_ratio = self.calculate_volume_confirmation(market_data)

        # ATR pour TP/SL
        atr = self.calculate_atr(market_data)

        # Génération du signal
        side = 'hold'
        confidence = 0.0
        reason = "Pas de cassure détectée"

        # Signal BUY - Cassure de résistance
        if self.is_breakout(current_price, resistance, 'up'):
            if high_volume:
                side = 'buy'
                # Confidence basée sur force de la cassure et volume
                breakout_strength = (current_price - resistance) / resistance
                volume_factor = min((volume_ratio - 1.0) / 2.0, 0.3)
                confidence = min(0.6 + (breakout_strength * 100) + volume_factor, 1.0)
                reason = (
                    f"Cassure haussière de résistance {resistance:.2f} "
                    f"avec volume x{volume_ratio:.1f}"
                )
            else:
                reason = f"Cassure résistance sans confirmation volume (x{volume_ratio:.1f})"

        # Signal SELL - Cassure de support
        elif self.is_breakout(current_price, support, 'down'):
            if high_volume:
                side = 'sell'
                breakout_strength = (support - current_price) / support
                volume_factor = min((volume_ratio - 1.0) / 2.0, 0.3)
                confidence = min(0.6 + (breakout_strength * 100) + volume_factor, 1.0)
                reason = (
                    f"Cassure baissière de support {support:.2f} "
                    f"avec volume x{volume_ratio:.1f}"
                )
            else:
                reason = f"Cassure support sans confirmation volume (x{volume_ratio:.1f})"

        # Ajustement confidence selon proximité récente des niveaux
        # Si le prix était proche du niveau récemment, c'est une meilleure cassure
        recent_closes = close.tail(5)
        if side == 'buy':
            was_near_resistance = (recent_closes < resistance).any()
            if was_near_resistance:
                confidence = min(confidence * 1.1, 1.0)

        elif side == 'sell':
            was_near_support = (recent_closes > support).any()
            if was_near_support:
                confidence = min(confidence * 1.1, 1.0)

        # Calcul TP/SL basés sur ATR
        if side == 'buy':
            tp = current_price + (atr * self.tp_multiplier)
            sl = max(resistance - (atr * 0.5), current_price - (atr * self.sl_multiplier))
        elif side == 'sell':
            tp = current_price - (atr * self.tp_multiplier)
            sl = min(support + (atr * 0.5), current_price + (atr * self.sl_multiplier))
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
