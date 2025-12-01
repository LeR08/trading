"""
Base Strategy Interface
Définit l'interface commune pour toutes les stratégies de trading
"""
from abc import ABC, abstractmethod
from typing import Dict, Optional
import pandas as pd


class BaseStrategy(ABC):
    """Classe de base abstraite pour les stratégies de trading"""

    def __init__(self, name: str):
        """
        Initialise la stratégie

        Args:
            name: Nom de la stratégie
        """
        self.name = name

    @abstractmethod
    def generate_signal(self, market_data: pd.DataFrame) -> Dict:
        """
        Génère un signal de trading basé sur les données de marché

        Args:
            market_data: DataFrame avec colonnes OHLCV (open, high, low, close, volume)
                        et timestamp

        Returns:
            Dict avec:
            {
                'side': 'buy' | 'sell' | 'hold',
                'confidence': float (0-1),  # Niveau de confiance du signal
                'price': float,              # Prix de référence
                'tp': float,                 # Take profit suggéré
                'sl': float,                 # Stop loss suggéré
                'reason': str                # Raison du signal
            }
        """
        pass

    def validate_market_data(self, market_data: pd.DataFrame) -> bool:
        """
        Valide que les données de marché sont correctes

        Args:
            market_data: DataFrame à valider

        Returns:
            True si les données sont valides
        """
        required_columns = ['open', 'high', 'low', 'close', 'volume']

        if market_data is None or market_data.empty:
            return False

        for col in required_columns:
            if col not in market_data.columns:
                return False

        return True

    def calculate_atr(self, market_data: pd.DataFrame, period: int = 14) -> float:
        """
        Calcule l'Average True Range pour volatilité

        Args:
            market_data: DataFrame OHLC
            period: Période pour ATR

        Returns:
            Valeur ATR
        """
        high = market_data['high']
        low = market_data['low']
        close = market_data['close'].shift(1)

        tr1 = high - low
        tr2 = abs(high - close)
        tr3 = abs(low - close)

        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean().iloc[-1]

        return atr

    def calculate_ema(self, series: pd.Series, period: int) -> pd.Series:
        """
        Calcule l'Exponential Moving Average

        Args:
            series: Série de prix
            period: Période EMA

        Returns:
            Série EMA
        """
        return series.ewm(span=period, adjust=False).mean()

    def calculate_rsi(self, series: pd.Series, period: int = 14) -> pd.Series:
        """
        Calcule le Relative Strength Index

        Args:
            series: Série de prix
            period: Période RSI

        Returns:
            Série RSI
        """
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    def __str__(self) -> str:
        return f"Strategy({self.name})"

    def __repr__(self) -> str:
        return self.__str__()
