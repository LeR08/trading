"""
Signal Engine - Aggregates indicator signals using weighted voting

Calculates confidence score and generates trading signals
"""
from dataclasses import dataclass
from typing import Dict, List, Optional
from enum import Enum
import logging

from ..indicators.technical_indicators import IndicatorSignal

logger = logging.getLogger(__name__)


class Direction(Enum):
    """Trading direction"""
    LONG = "long"
    SHORT = "short"
    NEUTRAL = "neutral"


@dataclass
class TradingSignal:
    """Represents a trading signal with confidence"""
    direction: Direction
    confidence: float  # 0-100%
    raw_score: float  # -1 to +1
    signals: Dict[str, IndicatorSignal]
    timeframe: int  # in minutes
    timestamp: int
    metadata: Dict[str, any]


class SignalGenerator:
    """
    Aggregates indicator signals using weighted voting system

    Confidence calculation:
    - Each indicator has a weight (sum of weights = 1.0)
    - Raw score = Σ(weight_i × signal_i) where signal_i ∈ [-1, +1]
    - Confidence = |raw_score| × 100
    - Direction is determined by sign of raw_score
    """

    def __init__(self, weights: Optional[Dict[str, float]] = None, confidence_threshold: float = 66.0):
        """
        Initialize signal generator

        Args:
            weights: Dictionary mapping indicator name to weight
            confidence_threshold: Minimum confidence to generate trading signal (default: 66%)
        """
        self.confidence_threshold = confidence_threshold

        # Default weights (sum = 1.0)
        self.weights = weights or {
            "ema_8": 0.08,
            "ema_21": 0.10,
            "sma_50": 0.08,
            "rsi_14": 0.10,
            "macd": 0.12,
            "atr_14": 0.08,
            "bollinger": 0.10,
            "stochastic": 0.08,
            "adx_14": 0.10,
            "cci_20": 0.06,
            "obv": 0.05,
            "vwap": 0.05,
        }

        # Validate weights sum to 1.0
        total_weight = sum(self.weights.values())
        if abs(total_weight - 1.0) > 0.01:
            logger.warning(f"Weights sum to {total_weight}, normalizing to 1.0")
            self.weights = {k: v / total_weight for k, v in self.weights.items()}

        logger.info(f"SignalGenerator initialized with confidence threshold: {confidence_threshold}%")
        logger.debug(f"Weights: {self.weights}")

    def calculate_raw_score(self, signals: Dict[str, IndicatorSignal]) -> float:
        """
        Calculate raw weighted score from indicator signals

        Args:
            signals: Dictionary of indicator signals

        Returns:
            Raw score in range [-1, +1]
        """
        total_score = 0.0
        total_weight = 0.0

        for indicator_name, signal in signals.items():
            weight = self.weights.get(indicator_name, 0.0)
            if weight > 0:
                # Use signal value (normalized -1 to +1)
                total_score += weight * signal.signal
                total_weight += weight

        # Normalize by actual weights used
        if total_weight > 0:
            return total_score / total_weight
        return 0.0

    def calculate_confidence(self, raw_score: float) -> float:
        """
        Calculate confidence from raw score

        Args:
            raw_score: Raw score in range [-1, +1]

        Returns:
            Confidence in range [0, 100]
        """
        return abs(raw_score) * 100

    def determine_direction(self, raw_score: float, confidence: float) -> Direction:
        """
        Determine trading direction based on score and confidence

        Args:
            raw_score: Raw score
            confidence: Confidence percentage

        Returns:
            Direction enum
        """
        if confidence < self.confidence_threshold:
            return Direction.NEUTRAL

        if raw_score > 0:
            return Direction.LONG
        elif raw_score < 0:
            return Direction.SHORT
        else:
            return Direction.NEUTRAL

    def generate_signal(
        self,
        signals: Dict[str, IndicatorSignal],
        timeframe: int,
        timestamp: int
    ) -> TradingSignal:
        """
        Generate trading signal from indicator signals

        Args:
            signals: Dictionary of indicator signals
            timeframe: Timeframe in minutes
            timestamp: Current timestamp

        Returns:
            TradingSignal with direction and confidence
        """
        # Calculate raw score
        raw_score = self.calculate_raw_score(signals)

        # Calculate confidence
        confidence = self.calculate_confidence(raw_score)

        # Determine direction
        direction = self.determine_direction(raw_score, confidence)

        # Collect metadata
        bullish_count = sum(1 for s in signals.values() if s.signal > 0)
        bearish_count = sum(1 for s in signals.values() if s.signal < 0)
        neutral_count = sum(1 for s in signals.values() if s.signal == 0)

        metadata = {
            "bullish_count": bullish_count,
            "bearish_count": bearish_count,
            "neutral_count": neutral_count,
            "total_indicators": len(signals),
            "meets_threshold": confidence >= self.confidence_threshold,
        }

        signal = TradingSignal(
            direction=direction,
            confidence=confidence,
            raw_score=raw_score,
            signals=signals,
            timeframe=timeframe,
            timestamp=timestamp,
            metadata=metadata
        )

        logger.info(
            f"Generated signal: {direction.value} | "
            f"Confidence: {confidence:.2f}% | "
            f"Raw score: {raw_score:.3f} | "
            f"TF: {timeframe}m"
        )
        logger.debug(f"Signal breakdown: {bullish_count}↑ {bearish_count}↓ {neutral_count}→")

        return signal

    def combine_timeframes(
        self,
        signals: Dict[int, TradingSignal],
        primary_timeframe: int = 3
    ) -> Optional[TradingSignal]:
        """
        Combine signals from multiple timeframes

        Strategy:
        - Primary timeframe (3m) provides the signal
        - Higher timeframe (15m) must confirm or be neutral
        - If conflict, return neutral

        Args:
            signals: Dictionary mapping timeframe to TradingSignal
            primary_timeframe: Primary timeframe for signal generation

        Returns:
            Combined TradingSignal or None
        """
        if primary_timeframe not in signals:
            logger.warning(f"Primary timeframe {primary_timeframe}m not in signals")
            return None

        primary = signals[primary_timeframe]

        # If primary is neutral, return neutral
        if primary.direction == Direction.NEUTRAL:
            logger.info("Primary timeframe is neutral")
            return primary

        # Check higher timeframes for confirmation
        higher_timeframes = [tf for tf in signals.keys() if tf > primary_timeframe]

        for tf in sorted(higher_timeframes):
            higher_signal = signals[tf]

            # If higher timeframe conflicts with primary, return neutral
            if higher_signal.direction != Direction.NEUTRAL and higher_signal.direction != primary.direction:
                logger.info(
                    f"Timeframe conflict: {primary_timeframe}m={primary.direction.value} "
                    f"vs {tf}m={higher_signal.direction.value}"
                )

                # Create neutral signal
                return TradingSignal(
                    direction=Direction.NEUTRAL,
                    confidence=0.0,
                    raw_score=0.0,
                    signals={},
                    timeframe=primary_timeframe,
                    timestamp=primary.timestamp,
                    metadata={"reason": "timeframe_conflict"}
                )

        # All higher timeframes confirm or are neutral
        logger.info(f"Signal confirmed across timeframes: {primary.direction.value}")
        return primary

    def get_signal_details(self, signal: TradingSignal) -> Dict[str, any]:
        """
        Get detailed breakdown of signal

        Args:
            signal: TradingSignal to analyze

        Returns:
            Dictionary with signal details
        """
        indicator_breakdown = {}

        for name, ind_signal in signal.signals.items():
            indicator_breakdown[name] = {
                "signal": ind_signal.signal,
                "strength": ind_signal.strength,
                "value": ind_signal.value,
                "weight": self.weights.get(name, 0.0),
                "contribution": self.weights.get(name, 0.0) * ind_signal.signal
            }

        return {
            "direction": signal.direction.value,
            "confidence": signal.confidence,
            "raw_score": signal.raw_score,
            "meets_threshold": signal.confidence >= self.confidence_threshold,
            "timeframe": signal.timeframe,
            "metadata": signal.metadata,
            "indicators": indicator_breakdown
        }
