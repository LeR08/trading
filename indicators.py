"""
Technical Indicators Module for Professional Trading
"""
import pandas as pd
import numpy as np
from ta.trend import MACD, EMAIndicator
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.volatility import BollingerBands, AverageTrueRange
from ta.volume import VolumeWeightedAveragePrice, OnBalanceVolumeIndicator
from config import Config


class TechnicalIndicators:
    """Calculate and analyze technical indicators"""

    def __init__(self, df):
        """
        Initialize with OHLCV dataframe
        df must have columns: ['time', 'open', 'high', 'low', 'close', 'volume']
        """
        self.df = df.copy()
        self.signals = {}

    def calculate_all(self):
        """Calculate all technical indicators"""
        self._calculate_ema()
        self._calculate_rsi()
        self._calculate_macd()
        self._calculate_bollinger_bands()
        self._calculate_stochastic()
        self._calculate_atr()
        self._calculate_volume_indicators()
        self._calculate_support_resistance()
        return self.df

    def _calculate_ema(self):
        """Calculate Exponential Moving Averages"""
        self.df['ema_short'] = EMAIndicator(
            close=self.df['close'],
            window=Config.EMA_SHORT
        ).ema_indicator()

        self.df['ema_medium'] = EMAIndicator(
            close=self.df['close'],
            window=Config.EMA_MEDIUM
        ).ema_indicator()

        self.df['ema_long'] = EMAIndicator(
            close=self.df['close'],
            window=Config.EMA_LONG
        ).ema_indicator()

    def _calculate_rsi(self):
        """Calculate Relative Strength Index"""
        rsi = RSIIndicator(
            close=self.df['close'],
            window=Config.RSI_PERIOD
        )
        self.df['rsi'] = rsi.rsi()

    def _calculate_macd(self):
        """Calculate MACD indicator"""
        macd = MACD(
            close=self.df['close'],
            window_fast=Config.MACD_FAST,
            window_slow=Config.MACD_SLOW,
            window_sign=Config.MACD_SIGNAL
        )
        self.df['macd'] = macd.macd()
        self.df['macd_signal'] = macd.macd_signal()
        self.df['macd_diff'] = macd.macd_diff()

    def _calculate_bollinger_bands(self):
        """Calculate Bollinger Bands"""
        bb = BollingerBands(
            close=self.df['close'],
            window=Config.BOLLINGER_PERIOD,
            window_dev=Config.BOLLINGER_STD
        )
        self.df['bb_upper'] = bb.bollinger_hband()
        self.df['bb_middle'] = bb.bollinger_mavg()
        self.df['bb_lower'] = bb.bollinger_lband()
        self.df['bb_width'] = bb.bollinger_wband()

    def _calculate_stochastic(self):
        """Calculate Stochastic Oscillator"""
        stoch = StochasticOscillator(
            high=self.df['high'],
            low=self.df['low'],
            close=self.df['close'],
            window=14,
            smooth_window=3
        )
        self.df['stoch_k'] = stoch.stoch()
        self.df['stoch_d'] = stoch.stoch_signal()

    def _calculate_atr(self):
        """Calculate Average True Range (volatility)"""
        atr = AverageTrueRange(
            high=self.df['high'],
            low=self.df['low'],
            close=self.df['close'],
            window=14
        )
        self.df['atr'] = atr.average_true_range()

    def _calculate_volume_indicators(self):
        """Calculate volume-based indicators"""
        # Volume Moving Average
        self.df['volume_ma'] = self.df['volume'].rolling(
            window=Config.VOLUME_MA_PERIOD
        ).mean()

        # On Balance Volume
        obv = OnBalanceVolumeIndicator(
            close=self.df['close'],
            volume=self.df['volume']
        )
        self.df['obv'] = obv.on_balance_volume()

        # Volume Ratio
        self.df['volume_ratio'] = self.df['volume'] / self.df['volume_ma']

    def _calculate_support_resistance(self):
        """Calculate support and resistance levels"""
        window = 20
        self.df['resistance'] = self.df['high'].rolling(window=window).max()
        self.df['support'] = self.df['low'].rolling(window=window).min()

    def get_trading_signals(self):
        """
        Analyze all indicators and generate trading signals
        Returns: dict with 'signal' ('buy', 'sell', 'hold') and 'strength' (0-100)
        """
        if len(self.df) < Config.EMA_LONG:
            return {'signal': 'hold', 'strength': 0, 'reason': 'Insufficient data'}

        latest = self.df.iloc[-1]
        prev = self.df.iloc[-2]

        buy_signals = 0
        sell_signals = 0
        total_weight = 0

        # 1. RSI Signal (Weight: 15)
        weight = 15
        if latest['rsi'] < Config.RSI_OVERSOLD:
            buy_signals += weight
        elif latest['rsi'] > Config.RSI_OVERBOUGHT:
            sell_signals += weight
        total_weight += weight

        # 2. MACD Signal (Weight: 20)
        weight = 20
        if latest['macd'] > latest['macd_signal'] and prev['macd'] <= prev['macd_signal']:
            buy_signals += weight  # Bullish crossover
        elif latest['macd'] < latest['macd_signal'] and prev['macd'] >= prev['macd_signal']:
            sell_signals += weight  # Bearish crossover
        total_weight += weight

        # 3. EMA Trend (Weight: 20)
        weight = 20
        if (latest['ema_short'] > latest['ema_medium'] > latest['ema_long'] and
            latest['close'] > latest['ema_short']):
            buy_signals += weight  # Strong uptrend
        elif (latest['ema_short'] < latest['ema_medium'] < latest['ema_long'] and
              latest['close'] < latest['ema_short']):
            sell_signals += weight  # Strong downtrend
        total_weight += weight

        # 4. Bollinger Bands (Weight: 15)
        weight = 15
        if latest['close'] < latest['bb_lower']:
            buy_signals += weight  # Oversold
        elif latest['close'] > latest['bb_upper']:
            sell_signals += weight  # Overbought
        total_weight += weight

        # 5. Stochastic (Weight: 10)
        weight = 10
        if latest['stoch_k'] < 20 and latest['stoch_k'] > latest['stoch_d']:
            buy_signals += weight  # Oversold with bullish cross
        elif latest['stoch_k'] > 80 and latest['stoch_k'] < latest['stoch_d']:
            sell_signals += weight  # Overbought with bearish cross
        total_weight += weight

        # 6. Volume Confirmation (Weight: 10)
        weight = 10
        if latest['volume_ratio'] > 1.5:
            # High volume confirms the trend
            if buy_signals > sell_signals:
                buy_signals += weight
            elif sell_signals > buy_signals:
                sell_signals += weight
        total_weight += weight

        # 7. Support/Resistance (Weight: 10)
        weight = 10
        price_near_support = abs(latest['close'] - latest['support']) / latest['close'] < 0.02
        price_near_resistance = abs(latest['close'] - latest['resistance']) / latest['close'] < 0.02

        if price_near_support:
            buy_signals += weight
        elif price_near_resistance:
            sell_signals += weight
        total_weight += weight

        # Calculate final signal
        buy_strength = (buy_signals / total_weight) * 100
        sell_strength = (sell_signals / total_weight) * 100

        # Decision threshold: need >60% strength to trade
        if buy_strength > 60 and buy_strength > sell_strength:
            signal = 'buy'
            strength = buy_strength
            reason = self._generate_reason('buy', latest)
        elif sell_strength > 60 and sell_strength > buy_strength:
            signal = 'sell'
            strength = sell_strength
            reason = self._generate_reason('sell', latest)
        else:
            signal = 'hold'
            strength = max(buy_strength, sell_strength)
            reason = 'No strong signal detected'

        return {
            'signal': signal,
            'strength': round(strength, 2),
            'reason': reason,
            'buy_strength': round(buy_strength, 2),
            'sell_strength': round(sell_strength, 2),
            'indicators': {
                'rsi': round(latest['rsi'], 2),
                'macd': round(latest['macd'], 2),
                'macd_signal': round(latest['macd_signal'], 2),
                'ema_short': round(latest['ema_short'], 2),
                'ema_medium': round(latest['ema_medium'], 2),
                'ema_long': round(latest['ema_long'], 2),
                'bb_upper': round(latest['bb_upper'], 2),
                'bb_lower': round(latest['bb_lower'], 2),
                'stoch_k': round(latest['stoch_k'], 2),
                'volume_ratio': round(latest['volume_ratio'], 2),
                'atr': round(latest['atr'], 2)
            }
        }

    def _generate_reason(self, signal_type, latest):
        """Generate human-readable reason for the signal"""
        reasons = []

        if signal_type == 'buy':
            if latest['rsi'] < Config.RSI_OVERSOLD:
                reasons.append(f"RSI oversold ({latest['rsi']:.1f})")
            if latest['macd'] > latest['macd_signal']:
                reasons.append("MACD bullish crossover")
            if latest['ema_short'] > latest['ema_medium'] > latest['ema_long']:
                reasons.append("Strong uptrend (EMA alignment)")
            if latest['close'] < latest['bb_lower']:
                reasons.append("Price below lower Bollinger Band")
            if latest['volume_ratio'] > 1.5:
                reasons.append(f"High volume confirmation ({latest['volume_ratio']:.1f}x)")
        else:  # sell
            if latest['rsi'] > Config.RSI_OVERBOUGHT:
                reasons.append(f"RSI overbought ({latest['rsi']:.1f})")
            if latest['macd'] < latest['macd_signal']:
                reasons.append("MACD bearish crossover")
            if latest['ema_short'] < latest['ema_medium'] < latest['ema_long']:
                reasons.append("Strong downtrend (EMA alignment)")
            if latest['close'] > latest['bb_upper']:
                reasons.append("Price above upper Bollinger Band")
            if latest['volume_ratio'] > 1.5:
                reasons.append(f"High volume confirmation ({latest['volume_ratio']:.1f}x)")

        return ", ".join(reasons) if reasons else "Multiple indicators aligned"
