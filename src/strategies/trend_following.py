"""
Enhanced Trend Following Strategy
Stratégie avancée avec 12 indicateurs techniques pour maximiser la fiabilité
"""
import pandas as pd
import numpy as np
from typing import Dict
from .base import BaseStrategy


class TrendFollowingStrategy(BaseStrategy):
    """
    Stratégie de suivi de tendance AMÉLIORÉE avec 12 indicateurs:
    1. EMA (9, 21, 50, 200)
    2. MACD
    3. RSI
    4. ADX (Average Directional Index)
    5. Bollinger Bands
    6. Stochastic Oscillator
    7. OBV (On-Balance Volume)
    8. Williams %R
    9. CCI (Commodity Channel Index)
    10. Volume Profile
    11. ATR (Volatility)
    12. Parabolic SAR

    Signal final = moyenne pondérée des 12 indicateurs
    Trade pris si confiance >= 66%
    """

    def __init__(
        self,
        ema_fast: int = 9,
        ema_medium: int = 21,
        ema_slow: int = 50,
        ema_trend: int = 200,
        macd_fast: int = 12,
        macd_slow: int = 26,
        macd_signal: int = 9,
        rsi_period: int = 14,
        adx_period: int = 14,
        bb_period: int = 20,
        bb_std: float = 2.0,
        stoch_period: int = 14,
        cci_period: int = 20,
        williams_period: int = 14,
        volume_ma: int = 20,
        tp_multiplier: float = 2.0,  # MODE AGRESSIF: R:R 2:1 pour petit capital
        sl_multiplier: float = 1.0   # Stop serré pour limiter les pertes
    ):
        """Initialise la stratégie avec 12 indicateurs"""
        super().__init__("TrendFollowing_Enhanced")
        self.ema_fast = ema_fast
        self.ema_medium = ema_medium
        self.ema_slow = ema_slow
        self.ema_trend = ema_trend
        self.macd_fast = macd_fast
        self.macd_slow = macd_slow
        self.macd_signal = macd_signal
        self.rsi_period = rsi_period
        self.adx_period = adx_period
        self.bb_period = bb_period
        self.bb_std = bb_std
        self.stoch_period = stoch_period
        self.cci_period = cci_period
        self.williams_period = williams_period
        self.volume_ma = volume_ma
        self.tp_multiplier = tp_multiplier
        self.sl_multiplier = sl_multiplier

    def calculate_macd(self, close: pd.Series) -> Dict:
        """Calcule MACD"""
        ema_fast = self.calculate_ema(close, self.macd_fast)
        ema_slow = self.calculate_ema(close, self.macd_slow)
        macd = ema_fast - ema_slow
        signal = macd.ewm(span=self.macd_signal, adjust=False).mean()
        histogram = macd - signal
        return {'macd': macd, 'signal': signal, 'histogram': histogram}

    def calculate_adx(self, high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """
        Calcule ADX (Average Directional Index)
        ADX > 25 = tendance forte
        ADX < 20 = pas de tendance
        """
        plus_dm = high.diff()
        minus_dm = -low.diff()

        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0

        tr = pd.concat([
            high - low,
            abs(high - close.shift(1)),
            abs(low - close.shift(1))
        ], axis=1).max(axis=1)

        atr = tr.rolling(window=period).mean()

        plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)

        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(window=period).mean()

        return adx, plus_di, minus_di

    def calculate_bollinger_bands(self, close: pd.Series) -> Dict:
        """Calcule Bollinger Bands"""
        middle = close.rolling(window=self.bb_period).mean()
        std = close.rolling(window=self.bb_period).std()
        upper = middle + (std * self.bb_std)
        lower = middle - (std * self.bb_std)
        return {'upper': upper, 'middle': middle, 'lower': lower}

    def calculate_stochastic(self, high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> Dict:
        """Calcule Stochastic Oscillator"""
        lowest_low = low.rolling(window=period).min()
        highest_high = high.rolling(window=period).max()

        k = 100 * (close - lowest_low) / (highest_high - lowest_low)
        d = k.rolling(window=3).mean()

        return {'k': k, 'd': d}

    def calculate_obv(self, close: pd.Series, volume: pd.Series) -> pd.Series:
        """Calcule On-Balance Volume"""
        obv = (np.sign(close.diff()) * volume).fillna(0).cumsum()
        return obv

    def calculate_williams_r(self, high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """Calcule Williams %R"""
        highest_high = high.rolling(window=period).max()
        lowest_low = low.rolling(window=period).min()

        williams = -100 * (highest_high - close) / (highest_high - lowest_low)
        return williams

    def calculate_cci(self, high: pd.Series, low: pd.Series, close: pd.Series, period: int = 20) -> pd.Series:
        """Calcule Commodity Channel Index"""
        tp = (high + low + close) / 3
        sma = tp.rolling(window=period).mean()
        mad = tp.rolling(window=period).apply(lambda x: np.abs(x - x.mean()).mean())

        cci = (tp - sma) / (0.015 * mad)
        return cci

    def calculate_parabolic_sar(self, high: pd.Series, low: pd.Series, af_start: float = 0.02, af_max: float = 0.2) -> pd.Series:
        """
        Calcule Parabolic SAR (Stop and Reverse)
        Simplifié pour performance
        """
        sar = pd.Series(index=high.index, dtype=float)
        sar.iloc[0] = low.iloc[0]

        # Version simplifiée : utiliser EMA comme proxy
        # Pour une vraie implémentation, voir bibliothèque TA-Lib
        sar = low.ewm(span=20, adjust=False).mean()

        return sar

    def generate_signal(self, market_data: pd.DataFrame) -> Dict:
        """
        Génère un signal basé sur 12 indicateurs avec scoring pondéré

        Pondération des indicateurs:
        - EMA Trend (200): 15%
        - EMA Alignment (9/21/50): 12%
        - MACD: 12%
        - ADX (force tendance): 10%
        - RSI: 8%
        - Stochastic: 8%
        - Bollinger Bands: 8%
        - OBV (volume): 7%
        - CCI: 6%
        - Williams %R: 6%
        - Volume confirmation: 5%
        - Parabolic SAR: 3%

        Total: 100%
        Trade pris si score >= 66%
        """
        if not self.validate_market_data(market_data):
            return {
                'side': 'hold',
                'confidence': 0.0,
                'price': 0.0,
                'tp': 0.0,
                'sl': 0.0,
                'reason': 'Données invalides'
            }

        close = market_data['close']
        high = market_data['high']
        low = market_data['low']
        volume = market_data['volume']

        # Calcul de tous les indicateurs
        ema_fast = self.calculate_ema(close, self.ema_fast)
        ema_medium = self.calculate_ema(close, self.ema_medium)
        ema_slow = self.calculate_ema(close, self.ema_slow)
        ema_trend = self.calculate_ema(close, self.ema_trend)

        macd_data = self.calculate_macd(close)
        rsi = self.calculate_rsi(close, self.rsi_period)
        adx, plus_di, minus_di = self.calculate_adx(high, low, close, self.adx_period)
        bb = self.calculate_bollinger_bands(close)
        stoch = self.calculate_stochastic(high, low, close, self.stoch_period)
        obv = self.calculate_obv(close, volume)
        williams = self.calculate_williams_r(high, low, close, self.williams_period)
        cci = self.calculate_cci(high, low, close, self.cci_period)
        sar = self.calculate_parabolic_sar(high, low)

        # Valeurs actuelles
        current_price = close.iloc[-1]
        current_ema_fast = ema_fast.iloc[-1]
        current_ema_medium = ema_medium.iloc[-1]
        current_ema_slow = ema_slow.iloc[-1]
        current_ema_trend = ema_trend.iloc[-1]

        current_macd = macd_data['macd'].iloc[-1]
        current_signal = macd_data['signal'].iloc[-1]
        current_histogram = macd_data['histogram'].iloc[-1]
        prev_histogram = macd_data['histogram'].iloc[-2]

        current_rsi = rsi.iloc[-1]
        current_adx = adx.iloc[-1]
        current_plus_di = plus_di.iloc[-1]
        current_minus_di = minus_di.iloc[-1]

        current_bb_upper = bb['upper'].iloc[-1]
        current_bb_middle = bb['middle'].iloc[-1]
        current_bb_lower = bb['lower'].iloc[-1]

        current_stoch_k = stoch['k'].iloc[-1]
        current_stoch_d = stoch['d'].iloc[-1]

        current_obv = obv.iloc[-1]
        prev_obv = obv.iloc[-2]

        current_williams = williams.iloc[-1]
        current_cci = cci.iloc[-1]
        current_sar = sar.iloc[-1]

        # Volume
        current_volume = volume.iloc[-1]
        avg_volume = volume.rolling(window=self.volume_ma).mean().iloc[-1]

        atr = self.calculate_atr(market_data)

        # === SCORING DES INDICATEURS ===

        scores = {
            'buy': 0.0,
            'sell': 0.0
        }

        # 1. EMA Trend 200 (15%)
        if current_price > current_ema_trend:
            scores['buy'] += 0.15
        else:
            scores['sell'] += 0.15

        # 2. EMA Alignment 9/21/50 (12%)
        if current_ema_fast > current_ema_medium > current_ema_slow:
            scores['buy'] += 0.12
        elif current_ema_fast < current_ema_medium < current_ema_slow:
            scores['sell'] += 0.12

        # 3. MACD (12%)
        macd_bullish = current_macd > current_signal
        macd_crossover_bull = current_histogram > 0 and prev_histogram <= 0
        macd_crossover_bear = current_histogram < 0 and prev_histogram >= 0

        if macd_bullish:
            scores['buy'] += 0.08
            if macd_crossover_bull:
                scores['buy'] += 0.04
        else:
            scores['sell'] += 0.08
            if macd_crossover_bear:
                scores['sell'] += 0.04

        # 4. ADX - Force de la tendance (10%)
        if current_adx > 25:  # Tendance forte
            if current_plus_di > current_minus_di:
                scores['buy'] += 0.10
            else:
                scores['sell'] += 0.10

        # 5. RSI (8%)
        if current_rsi < 30:  # Survente = potentiel achat
            scores['buy'] += 0.08
        elif current_rsi > 70:  # Surachat = potentiel vente
            scores['sell'] += 0.08
        elif 40 < current_rsi < 60:  # Zone neutre
            pass
        elif current_rsi > 50:
            scores['buy'] += 0.04
        else:
            scores['sell'] += 0.04

        # 6. Stochastic (8%)
        if current_stoch_k < 20 and current_stoch_k > current_stoch_d:
            scores['buy'] += 0.08
        elif current_stoch_k > 80 and current_stoch_k < current_stoch_d:
            scores['sell'] += 0.08

        # 7. Bollinger Bands (8%)
        bb_position = (current_price - current_bb_lower) / (current_bb_upper - current_bb_lower)
        if bb_position < 0.2:  # Proche bande basse
            scores['buy'] += 0.08
        elif bb_position > 0.8:  # Proche bande haute
            scores['sell'] += 0.08

        # 8. OBV - Volume (7%)
        if current_obv > prev_obv:
            scores['buy'] += 0.07
        else:
            scores['sell'] += 0.07

        # 9. CCI (6%)
        if current_cci < -100:
            scores['buy'] += 0.06
        elif current_cci > 100:
            scores['sell'] += 0.06

        # 10. Williams %R (6%)
        if current_williams < -80:
            scores['buy'] += 0.06
        elif current_williams > -20:
            scores['sell'] += 0.06

        # 11. Volume confirmation (5%)
        if current_volume > avg_volume * 1.2:
            # Fort volume confirme la tendance actuelle
            if scores['buy'] > scores['sell']:
                scores['buy'] += 0.05
            else:
                scores['sell'] += 0.05

        # 12. Parabolic SAR (3%)
        if current_price > current_sar:
            scores['buy'] += 0.03
        else:
            scores['sell'] += 0.03

        # === DÉTERMINER LE SIGNAL ===

        buy_score = scores['buy']
        sell_score = scores['sell']

        # Seuil de confiance à 66% (0.66)
        confidence_threshold = 0.66

        if buy_score >= confidence_threshold and buy_score > sell_score:
            side = 'buy'
            confidence = buy_score
            reason = f"STRONG BUY: {int(buy_score*100)}% confiance - {self._get_top_indicators('buy', scores)}"
        elif sell_score >= confidence_threshold and sell_score > buy_score:
            side = 'sell'
            confidence = sell_score
            reason = f"STRONG SELL: {int(sell_score*100)}% confiance - {self._get_top_indicators('sell', scores)}"
        else:
            side = 'hold'
            confidence = max(buy_score, sell_score)
            reason = f"Signal trop faible - Buy:{int(buy_score*100)}% Sell:{int(sell_score*100)}% (seuil: 66%)"

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

    def _get_top_indicators(self, direction: str, scores: Dict) -> str:
        """Retourne les indicateurs principaux qui supportent le signal"""
        indicators = []

        if direction == 'buy':
            if scores.get('ema_trend', 0) > 0:
                indicators.append("EMA200")
            if scores.get('macd', 0) > 0:
                indicators.append("MACD")
            if scores.get('adx', 0) > 0:
                indicators.append("ADX")

        return ", ".join(indicators[:3]) if indicators else "Multi-indicateurs"
