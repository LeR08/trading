"""
Technical Indicators Module - 12 Indicators Implementation

Each indicator returns a normalized signal: +1 (bullish), -1 (bearish), 0 (neutral)
"""
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class IndicatorSignal:
    """Represents a signal from a technical indicator"""
    name: str
    value: float  # Actual indicator value
    signal: float  # Normalized signal: -1, 0, +1
    strength: float  # Signal strength [0, 1]
    metadata: Dict[str, Any] = None


class TechnicalIndicators:
    """
    Calculates 12 technical indicators and generates normalized signals

    Indicators:
    1. EMA(8)
    2. EMA(21)
    3. SMA(50)
    4. RSI(14)
    5. MACD(12,26,9)
    6. ATR(14)
    7. Bollinger Bands(20,2)
    8. Stochastic(14,3)
    9. ADX(14)
    10. CCI(20)
    11. OBV
    12. VWAP
    """

    def __init__(self):
        """Initialize indicators calculator"""
        self.indicators_config = {
            "ema_8": {"period": 8, "weight": 0.08},
            "ema_21": {"period": 21, "weight": 0.10},
            "sma_50": {"period": 50, "weight": 0.08},
            "rsi_14": {"period": 14, "weight": 0.10},
            "macd": {"fast": 12, "slow": 26, "signal": 9, "weight": 0.12},
            "atr_14": {"period": 14, "weight": 0.08},
            "bollinger": {"period": 20, "std": 2, "weight": 0.10},
            "stochastic": {"period": 14, "smooth": 3, "weight": 0.08},
            "adx_14": {"period": 14, "weight": 0.10},
            "cci_20": {"period": 20, "weight": 0.06},
            "obv": {"weight": 0.05},
            "vwap": {"weight": 0.05},
        }

    # ==================== Moving Averages ====================

    @staticmethod
    def calculate_ema(series: pd.Series, period: int) -> pd.Series:
        """Calculate Exponential Moving Average"""
        return series.ewm(span=period, adjust=False).mean()

    @staticmethod
    def calculate_sma(series: pd.Series, period: int) -> pd.Series:
        """Calculate Simple Moving Average"""
        return series.rolling(window=period).mean()

    def ema_signal(self, df: pd.DataFrame, period: int) -> IndicatorSignal:
        """
        EMA crossover signal
        Signal: +1 if price > EMA (bullish), -1 if price < EMA (bearish)
        """
        ema = self.calculate_ema(df['close'], period)
        current_price = df['close'].iloc[-1]
        current_ema = ema.iloc[-1]

        # Calculate distance as percentage
        distance_pct = (current_price - current_ema) / current_ema * 100

        # Normalize signal
        if distance_pct > 0.1:  # > 0.1% above EMA
            signal = 1.0
            strength = min(abs(distance_pct) / 2.0, 1.0)
        elif distance_pct < -0.1:  # > 0.1% below EMA
            signal = -1.0
            strength = min(abs(distance_pct) / 2.0, 1.0)
        else:
            signal = 0.0
            strength = 0.0

        return IndicatorSignal(
            name=f"EMA({period})",
            value=current_ema,
            signal=signal,
            strength=strength,
            metadata={"distance_pct": distance_pct}
        )

    def sma_signal(self, df: pd.DataFrame, period: int) -> IndicatorSignal:
        """SMA crossover signal"""
        sma = self.calculate_sma(df['close'], period)
        current_price = df['close'].iloc[-1]
        current_sma = sma.iloc[-1]

        distance_pct = (current_price - current_sma) / current_sma * 100

        if distance_pct > 0.2:
            signal = 1.0
            strength = min(abs(distance_pct) / 3.0, 1.0)
        elif distance_pct < -0.2:
            signal = -1.0
            strength = min(abs(distance_pct) / 3.0, 1.0)
        else:
            signal = 0.0
            strength = 0.0

        return IndicatorSignal(
            name=f"SMA({period})",
            value=current_sma,
            signal=signal,
            strength=strength,
            metadata={"distance_pct": distance_pct}
        )

    # ==================== RSI ====================

    @staticmethod
    def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
        """Calculate Relative Strength Index"""
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def rsi_signal(self, df: pd.DataFrame, period: int = 14) -> IndicatorSignal:
        """
        RSI signal
        Signal: +1 if RSI < 30 (oversold), -1 if RSI > 70 (overbought), 0 otherwise
        """
        rsi = self.calculate_rsi(df['close'], period)
        current_rsi = rsi.iloc[-1]

        if current_rsi < 30:
            signal = 1.0
            strength = (30 - current_rsi) / 30
        elif current_rsi > 70:
            signal = -1.0
            strength = (current_rsi - 70) / 30
        else:
            # Neutral zone with weak signals
            if current_rsi < 45:
                signal = 0.5
                strength = (45 - current_rsi) / 15
            elif current_rsi > 55:
                signal = -0.5
                strength = (current_rsi - 55) / 15
            else:
                signal = 0.0
                strength = 0.0

        return IndicatorSignal(
            name=f"RSI({period})",
            value=current_rsi,
            signal=signal,
            strength=strength,
            metadata={"level": "oversold" if current_rsi < 30 else "overbought" if current_rsi > 70 else "neutral"}
        )

    # ==================== MACD ====================

    @staticmethod
    def calculate_macd(series: pd.Series, fast: int = 12, slow: int = 26, signal_period: int = 9) -> Dict[str, pd.Series]:
        """Calculate MACD indicator"""
        ema_fast = series.ewm(span=fast, adjust=False).mean()
        ema_slow = series.ewm(span=slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
        histogram = macd_line - signal_line

        return {
            "macd": macd_line,
            "signal": signal_line,
            "histogram": histogram
        }

    def macd_signal(self, df: pd.DataFrame) -> IndicatorSignal:
        """
        MACD signal
        Signal: +1 if MACD crosses above signal (bullish), -1 if crosses below (bearish)
        """
        macd_data = self.calculate_macd(df['close'])
        histogram = macd_data["histogram"]
        current_hist = histogram.iloc[-1]
        prev_hist = histogram.iloc[-2]

        # Check for crossover
        if prev_hist <= 0 and current_hist > 0:
            signal = 1.0
            strength = 1.0
        elif prev_hist >= 0 and current_hist < 0:
            signal = -1.0
            strength = 1.0
        else:
            # Use histogram value for signal
            if current_hist > 0:
                signal = 0.5
                strength = min(abs(current_hist) / df['close'].iloc[-1] * 1000, 1.0)
            elif current_hist < 0:
                signal = -0.5
                strength = min(abs(current_hist) / df['close'].iloc[-1] * 1000, 1.0)
            else:
                signal = 0.0
                strength = 0.0

        return IndicatorSignal(
            name="MACD(12,26,9)",
            value=current_hist,
            signal=signal,
            strength=strength,
            metadata={"macd": macd_data["macd"].iloc[-1], "signal_line": macd_data["signal"].iloc[-1]}
        )

    # ==================== ATR ====================

    @staticmethod
    def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Average True Range"""
        high = df['high']
        low = df['low']
        close = df['close']

        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())

        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        return atr

    def atr_signal(self, df: pd.DataFrame, period: int = 14) -> IndicatorSignal:
        """
        ATR volatility signal
        Signal: Used for stop-loss calculation, not directional
        Higher ATR = higher volatility
        """
        atr = self.calculate_atr(df, period)
        current_atr = atr.iloc[-1]
        atr_mean = atr.tail(50).mean()

        # Compare current ATR to mean
        volatility_ratio = current_atr / atr_mean if atr_mean > 0 else 1.0

        # ATR doesn't give directional signal, but high volatility might suggest caution
        signal = 0.0  # Neutral
        strength = 0.0

        return IndicatorSignal(
            name=f"ATR({period})",
            value=current_atr,
            signal=signal,
            strength=strength,
            metadata={"volatility_ratio": volatility_ratio, "is_high_volatility": volatility_ratio > 1.5}
        )

    # ==================== Bollinger Bands ====================

    @staticmethod
    def calculate_bollinger_bands(series: pd.Series, period: int = 20, std: int = 2) -> Dict[str, pd.Series]:
        """Calculate Bollinger Bands"""
        sma = series.rolling(window=period).mean()
        rolling_std = series.rolling(window=period).std()

        upper_band = sma + (rolling_std * std)
        lower_band = sma - (rolling_std * std)

        return {
            "upper": upper_band,
            "middle": sma,
            "lower": lower_band
        }

    def bollinger_signal(self, df: pd.DataFrame, period: int = 20, std: int = 2) -> IndicatorSignal:
        """
        Bollinger Bands signal
        Signal: +1 if price near lower band (oversold), -1 if near upper band (overbought)
        """
        bb = self.calculate_bollinger_bands(df['close'], period, std)
        current_price = df['close'].iloc[-1]
        upper = bb['upper'].iloc[-1]
        lower = bb['lower'].iloc[-1]
        middle = bb['middle'].iloc[-1]

        # Calculate position within bands (0 = lower, 0.5 = middle, 1 = upper)
        band_width = upper - lower
        if band_width > 0:
            position = (current_price - lower) / band_width
        else:
            position = 0.5

        # Generate signal
        if position < 0.2:  # Near lower band
            signal = 1.0
            strength = 1.0 - (position / 0.2)
        elif position > 0.8:  # Near upper band
            signal = -1.0
            strength = (position - 0.8) / 0.2
        else:
            signal = 0.0
            strength = 0.0

        return IndicatorSignal(
            name=f"Bollinger({period},{std})",
            value=current_price,
            signal=signal,
            strength=strength,
            metadata={"position": position, "upper": upper, "lower": lower}
        )

    # ==================== Stochastic Oscillator ====================

    @staticmethod
    def calculate_stochastic(df: pd.DataFrame, period: int = 14, smooth: int = 3) -> Dict[str, pd.Series]:
        """Calculate Stochastic Oscillator"""
        low_min = df['low'].rolling(window=period).min()
        high_max = df['high'].rolling(window=period).max()

        k = 100 * (df['close'] - low_min) / (high_max - low_min)
        d = k.rolling(window=smooth).mean()

        return {"k": k, "d": d}

    def stochastic_signal(self, df: pd.DataFrame, period: int = 14, smooth: int = 3) -> IndicatorSignal:
        """
        Stochastic signal
        Signal: +1 if oversold and crossing up, -1 if overbought and crossing down
        """
        stoch = self.calculate_stochastic(df, period, smooth)
        k = stoch['k'].iloc[-1]
        d = stoch['d'].iloc[-1]

        if k < 20 and d < 20:  # Oversold
            signal = 1.0
            strength = (20 - k) / 20
        elif k > 80 and d > 80:  # Overbought
            signal = -1.0
            strength = (k - 80) / 20
        else:
            signal = 0.0
            strength = 0.0

        return IndicatorSignal(
            name=f"Stochastic({period},{smooth})",
            value=k,
            signal=signal,
            strength=strength,
            metadata={"k": k, "d": d}
        )

    # ==================== ADX ====================

    @staticmethod
    def calculate_adx(df: pd.DataFrame, period: int = 14) -> Dict[str, pd.Series]:
        """Calculate Average Directional Index"""
        high = df['high']
        low = df['low']
        close = df['close']

        # Calculate +DM and -DM
        plus_dm = high.diff()
        minus_dm = -low.diff()

        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0

        # Calculate TR
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        # Calculate smoothed values
        atr = tr.rolling(window=period).mean()
        plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)

        # Calculate DX and ADX
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(window=period).mean()

        return {"adx": adx, "plus_di": plus_di, "minus_di": minus_di}

    def adx_signal(self, df: pd.DataFrame, period: int = 14) -> IndicatorSignal:
        """
        ADX signal
        Signal: Direction from +DI/-DI, strength from ADX value
        """
        adx_data = self.calculate_adx(df, period)
        adx = adx_data['adx'].iloc[-1]
        plus_di = adx_data['plus_di'].iloc[-1]
        minus_di = adx_data['minus_di'].iloc[-1]

        # ADX > 25 indicates strong trend
        is_trending = adx > 25

        if is_trending:
            if plus_di > minus_di:
                signal = 1.0
                strength = min(adx / 50, 1.0)
            else:
                signal = -1.0
                strength = min(adx / 50, 1.0)
        else:
            signal = 0.0
            strength = 0.0

        return IndicatorSignal(
            name=f"ADX({period})",
            value=adx,
            signal=signal,
            strength=strength,
            metadata={"plus_di": plus_di, "minus_di": minus_di, "trending": is_trending}
        )

    # ==================== CCI ====================

    @staticmethod
    def calculate_cci(df: pd.DataFrame, period: int = 20) -> pd.Series:
        """Calculate Commodity Channel Index"""
        tp = (df['high'] + df['low'] + df['close']) / 3
        sma = tp.rolling(window=period).mean()
        mad = tp.rolling(window=period).apply(lambda x: np.abs(x - x.mean()).mean())

        cci = (tp - sma) / (0.015 * mad)
        return cci

    def cci_signal(self, df: pd.DataFrame, period: int = 20) -> IndicatorSignal:
        """
        CCI signal
        Signal: +1 if CCI < -100 (oversold), -1 if CCI > 100 (overbought)
        """
        cci = self.calculate_cci(df, period)
        current_cci = cci.iloc[-1]

        if current_cci < -100:
            signal = 1.0
            strength = min(abs(current_cci + 100) / 100, 1.0)
        elif current_cci > 100:
            signal = -1.0
            strength = min((current_cci - 100) / 100, 1.0)
        else:
            signal = 0.0
            strength = 0.0

        return IndicatorSignal(
            name=f"CCI({period})",
            value=current_cci,
            signal=signal,
            strength=strength,
            metadata={}
        )

    # ==================== OBV ====================

    @staticmethod
    def calculate_obv(df: pd.DataFrame) -> pd.Series:
        """Calculate On Balance Volume"""
        obv = (np.sign(df['close'].diff()) * df['volume']).fillna(0).cumsum()
        return obv

    def obv_signal(self, df: pd.DataFrame) -> IndicatorSignal:
        """
        OBV signal
        Signal: Based on OBV trend vs price trend (divergence)
        """
        obv = self.calculate_obv(df)
        obv_ema = obv.ewm(span=20).mean()

        current_obv = obv.iloc[-1]
        current_obv_ema = obv_ema.iloc[-1]

        # Check if OBV is rising or falling
        obv_trend = current_obv - obv_ema.iloc[-10]
        price_trend = df['close'].iloc[-1] - df['close'].iloc[-10]

        # Divergence check
        if obv_trend > 0 and price_trend > 0:
            signal = 1.0
            strength = 0.5
        elif obv_trend < 0 and price_trend < 0:
            signal = -1.0
            strength = 0.5
        else:
            # Divergence detected
            signal = 0.0
            strength = 0.0

        return IndicatorSignal(
            name="OBV",
            value=current_obv,
            signal=signal,
            strength=strength,
            metadata={"obv_ema": current_obv_ema}
        )

    # ==================== VWAP ====================

    @staticmethod
    def calculate_vwap(df: pd.DataFrame) -> pd.Series:
        """Calculate Volume Weighted Average Price"""
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        vwap = (typical_price * df['volume']).cumsum() / df['volume'].cumsum()
        return vwap

    def vwap_signal(self, df: pd.DataFrame) -> IndicatorSignal:
        """
        VWAP signal
        Signal: +1 if price > VWAP (bullish), -1 if price < VWAP (bearish)
        """
        # For intraday VWAP, use only today's data (last 480 candles for 3min = 24h)
        recent_df = df.tail(480)
        vwap = self.calculate_vwap(recent_df)

        current_price = df['close'].iloc[-1]
        current_vwap = vwap.iloc[-1]

        distance_pct = (current_price - current_vwap) / current_vwap * 100

        if distance_pct > 0.1:
            signal = 1.0
            strength = min(abs(distance_pct) / 2.0, 1.0)
        elif distance_pct < -0.1:
            signal = -1.0
            strength = min(abs(distance_pct) / 2.0, 1.0)
        else:
            signal = 0.0
            strength = 0.0

        return IndicatorSignal(
            name="VWAP",
            value=current_vwap,
            signal=signal,
            strength=strength,
            metadata={"distance_pct": distance_pct}
        )

    # ==================== Main Calculation Method ====================

    def calculate_all_indicators(self, df: pd.DataFrame) -> Dict[str, IndicatorSignal]:
        """
        Calculate all 12 indicators and return their signals

        Args:
            df: DataFrame with OHLCV data

        Returns:
            Dictionary mapping indicator name to IndicatorSignal
        """
        if df.empty or len(df) < 50:
            logger.warning("Insufficient data for indicator calculation")
            return {}

        signals = {}

        try:
            signals["ema_8"] = self.ema_signal(df, 8)
            signals["ema_21"] = self.ema_signal(df, 21)
            signals["sma_50"] = self.sma_signal(df, 50)
            signals["rsi_14"] = self.rsi_signal(df, 14)
            signals["macd"] = self.macd_signal(df)
            signals["atr_14"] = self.atr_signal(df, 14)
            signals["bollinger"] = self.bollinger_signal(df, 20, 2)
            signals["stochastic"] = self.stochastic_signal(df, 14, 3)
            signals["adx_14"] = self.adx_signal(df, 14)
            signals["cci_20"] = self.cci_signal(df, 20)
            signals["obv"] = self.obv_signal(df)
            signals["vwap"] = self.vwap_signal(df)

        except Exception as e:
            logger.error(f"Error calculating indicators: {e}", exc_info=True)

        return signals
