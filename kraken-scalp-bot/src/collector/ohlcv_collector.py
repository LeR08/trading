"""
OHLCV Data Collector - Fetches and manages candlestick data
"""
import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
import logging
import pandas as pd
import numpy as np

from .kraken_client import KrakenClient

logger = logging.getLogger(__name__)


@dataclass
class Candle:
    """Represents a single OHLCV candle"""
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    vwap: float
    volume: float
    count: int
    is_closed: bool = True


class OHLCVCollector:
    """
    Collects OHLCV data from Kraken for multiple timeframes
    Supports both closed candles and partial (current) candle
    """

    # Kraken interval mapping (minutes -> Kraken interval code)
    # Valid Kraken intervals: 1, 5, 15, 30, 60, 240, 1440, 10080, 21600
    INTERVAL_MAP = {
        1: 1,
        5: 5,
        15: 15,
        30: 30,
        60: 60,
        240: 240,
        1440: 1440,
        10080: 10080,
        21600: 21600,
    }

    def __init__(
        self,
        client: KrakenClient,
        pair: str = "XBTUSD",
        timeframes: List[int] = [3, 15],
        use_partial_candle: bool = True
    ):
        """
        Initialize OHLCV collector

        Args:
            client: Kraken API client
            pair: Trading pair (Kraken format, e.g., 'XBTUSD')
            timeframes: List of timeframes in minutes to collect
            use_partial_candle: Whether to include partial (current) candle
        """
        self.client = client
        self.pair = pair
        self.timeframes = timeframes
        self.use_partial_candle = use_partial_candle

        # Validate timeframes
        for tf in timeframes:
            if tf not in self.INTERVAL_MAP:
                raise ValueError(f"Invalid timeframe {tf}. Must be one of {list(self.INTERVAL_MAP.keys())}")

        # Cache for last timestamp per timeframe
        self._last_timestamps: Dict[int, int] = {}

        # Data storage
        self._data: Dict[int, pd.DataFrame] = {}

    async def fetch_ohlcv(
        self,
        timeframe: int,
        since: Optional[int] = None,
        limit: int = 720
    ) -> Tuple[pd.DataFrame, Optional[Candle]]:
        """
        Fetch OHLCV data for a specific timeframe

        Args:
            timeframe: Timeframe in minutes
            since: Fetch data since this timestamp
            limit: Maximum number of candles to fetch

        Returns:
            Tuple of (DataFrame with closed candles, partial candle or None)
        """
        interval = self.INTERVAL_MAP.get(timeframe)
        if not interval:
            raise ValueError(f"Invalid timeframe: {timeframe}")

        try:
            result = await self.client.get_ohlc(
                pair=self.pair,
                interval=interval,
                since=since
            )

            # Extract OHLC data (result format varies, could be under pair name)
            ohlc_data = None
            for key, value in result.items():
                if key != "last" and isinstance(value, list):
                    ohlc_data = value
                    break

            if not ohlc_data:
                logger.warning(f"No OHLC data returned for {self.pair} {timeframe}m")
                return pd.DataFrame(), None

            # Parse candles
            candles = []
            for item in ohlc_data:
                candles.append(Candle(
                    timestamp=int(item[0]),
                    open=float(item[1]),
                    high=float(item[2]),
                    low=float(item[3]),
                    close=float(item[4]),
                    vwap=float(item[5]),
                    volume=float(item[6]),
                    count=int(item[7]),
                    is_closed=True
                ))

            # Check if last candle is partial (not closed yet)
            partial_candle = None
            if candles and self.use_partial_candle:
                last_candle = candles[-1]
                current_time = int(datetime.now(timezone.utc).timestamp())
                candle_end_time = last_candle.timestamp + (timeframe * 60)

                # If current time < candle end time, it's partial
                if current_time < candle_end_time:
                    partial_candle = candles.pop()
                    partial_candle.is_closed = False
                    logger.debug(f"Partial candle detected for {timeframe}m: {partial_candle}")

            # Convert to DataFrame
            if candles:
                df = pd.DataFrame([
                    {
                        'timestamp': c.timestamp,
                        'datetime': pd.to_datetime(c.timestamp, unit='s'),
                        'open': c.open,
                        'high': c.high,
                        'low': c.low,
                        'close': c.close,
                        'vwap': c.vwap,
                        'volume': c.volume,
                        'count': c.count,
                    }
                    for c in candles
                ])
                df.set_index('datetime', inplace=True)
            else:
                df = pd.DataFrame()

            # Update last timestamp
            if result.get("last"):
                self._last_timestamps[timeframe] = int(result["last"])

            logger.info(f"Fetched {len(df)} closed candles for {self.pair} {timeframe}m")
            if partial_candle:
                logger.info(f"Partial candle: close={partial_candle.close:.2f}")

            return df, partial_candle

        except Exception as e:
            logger.error(f"Error fetching OHLCV for {timeframe}m: {e}", exc_info=True)
            return pd.DataFrame(), None

    async def fetch_all_timeframes(self) -> Dict[int, Tuple[pd.DataFrame, Optional[Candle]]]:
        """
        Fetch OHLCV data for all configured timeframes concurrently

        Returns:
            Dictionary mapping timeframe -> (DataFrame, partial_candle)
        """
        tasks = []
        for tf in self.timeframes:
            since = self._last_timestamps.get(tf)
            tasks.append(self.fetch_ohlcv(tf, since=since))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        output = {}
        for tf, result in zip(self.timeframes, results):
            if isinstance(result, Exception):
                logger.error(f"Failed to fetch {tf}m: {result}")
                output[tf] = (pd.DataFrame(), None)
            else:
                output[tf] = result
                # Update internal cache
                df, partial = result
                if not df.empty:
                    self._data[tf] = df

        return output

    def get_latest_data(self, timeframe: int, limit: int = 100) -> pd.DataFrame:
        """
        Get latest cached data for a timeframe

        Args:
            timeframe: Timeframe in minutes
            limit: Number of candles to return

        Returns:
            DataFrame with latest candles
        """
        if timeframe not in self._data:
            return pd.DataFrame()

        df = self._data[timeframe]
        return df.tail(limit).copy()

    async def get_current_price(self) -> Optional[float]:
        """
        Get current price from ticker

        Returns:
            Current price or None
        """
        try:
            ticker = await self.client.get_ticker(self.pair)
            # Ticker result format: {'PAIR': {'c': [price, volume], ...}}
            for key, value in ticker.items():
                if isinstance(value, dict) and 'c' in value:
                    return float(value['c'][0])
            return None
        except Exception as e:
            logger.error(f"Error fetching current price: {e}")
            return None

    async def initialize(self, lookback_periods: int = 200):
        """
        Initialize collector by fetching historical data

        Args:
            lookback_periods: Number of candles to fetch initially for each timeframe
        """
        logger.info(f"Initializing collector for {self.pair} with timeframes {self.timeframes}")

        for tf in self.timeframes:
            try:
                # Calculate 'since' timestamp for lookback
                now = datetime.now(timezone.utc)
                since_dt = now - timedelta(minutes=tf * lookback_periods)
                since_ts = int(since_dt.timestamp())

                df, _ = await self.fetch_ohlcv(tf, since=since_ts)
                if not df.empty:
                    self._data[tf] = df
                    logger.info(f"Initialized {tf}m with {len(df)} candles")
                else:
                    logger.warning(f"No initial data for {tf}m")

                # Rate limiting
                await asyncio.sleep(1)

            except Exception as e:
                logger.error(f"Error initializing {tf}m: {e}", exc_info=True)

        logger.info("Collector initialization complete")

    def get_data_summary(self) -> Dict[int, Dict[str, any]]:
        """
        Get summary of available data

        Returns:
            Dictionary with summary per timeframe
        """
        summary = {}
        for tf, df in self._data.items():
            if df.empty:
                summary[tf] = {"count": 0, "start": None, "end": None}
            else:
                summary[tf] = {
                    "count": len(df),
                    "start": df.index[0],
                    "end": df.index[-1],
                    "last_close": df['close'].iloc[-1]
                }
        return summary
