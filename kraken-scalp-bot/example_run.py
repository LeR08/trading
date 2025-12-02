"""
Example Run - Demonstrates bot usage in different modes
"""
import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.bot import KrakenScalpBot


async def run_paper_mode():
    """Run bot in paper trading mode"""
    print("="*60)
    print("Running in PAPER MODE (simulation)")
    print("="*60)

    bot = KrakenScalpBot(config_path="config/config.yaml")
    await bot.run()


async def example_backtest():
    """Example backtest execution"""
    print("="*60)
    print("Example Backtest")
    print("="*60)

    from src.collector.kraken_client import KrakenClient
    from src.backtest.backtest_engine import BacktestEngine
    from src.indicators.technical_indicators import TechnicalIndicators
    from src.signal_engine.signal_generator import SignalGenerator
    import pandas as pd

    # Initialize components
    async with KrakenClient() as client:
        # Fetch historical data (1 week of 3min candles)
        print("Fetching historical data...")
        result = await client.get_ohlc(pair="XBTUSD", interval=3)

        # Parse OHLC data
        ohlc_data = None
        for key, value in result.items():
            if key != "last" and isinstance(value, list):
                ohlc_data = value
                break

        if not ohlc_data:
            print("No data received")
            return

        # Convert to DataFrame
        df = pd.DataFrame(ohlc_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'vwap', 'volume', 'count'])
        df = df.astype({
            'timestamp': 'int64',
            'open': 'float64',
            'high': 'float64',
            'low': 'float64',
            'close': 'float64',
            'volume': 'float64'
        })
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='s')
        df.set_index('datetime', inplace=True)

        print(f"Loaded {len(df)} candles")
        print(f"Date range: {df.index[0]} to {df.index[-1]}")

        # Initialize backtest
        backtest = BacktestEngine(
            initial_equity=10000.0,
            leverage=3,
            slippage_pct=0.001
        )

        # Initialize indicators and signal generator
        indicators = TechnicalIndicators()
        signal_gen = SignalGenerator(confidence_threshold=66.0)

        # Run backtest
        print("\nRunning backtest...")

        for i in range(100, len(df)):
            # Get historical window
            window = df.iloc[max(0, i-100):i]

            # Calculate indicators
            signals = indicators.calculate_all_indicators(window)

            if not signals:
                continue

            # Generate signal
            trading_signal = signal_gen.generate_signal(signals, timeframe=3, timestamp=int(df.index[i].timestamp()))

            # Check open positions for exit
            current_candle = df.iloc[i]
            backtest.check_exits(
                timestamp=df.index[i],
                high=current_candle['high'],
                low=current_candle['low'],
                close=current_candle['close']
            )

            # Check for entry signal
            if trading_signal.confidence >= 66.0 and len(backtest.open_trades) == 0:
                # Calculate ATR for SL
                atr = indicators.calculate_atr(window, 14).iloc[-1]
                current_price = current_candle['close']

                direction = "long" if trading_signal.direction.name == "LONG" else "short"

                # Simple SL/TP calculation
                if direction == "long":
                    sl = current_price - (atr * 1.0)
                    tp = current_price + (atr * 0.7)
                else:
                    sl = current_price + (atr * 1.0)
                    tp = current_price - (atr * 0.7)

                # Calculate position size (simple: 1% risk)
                risk_amount = backtest.equity * 0.01
                risk_per_unit = abs(current_price - sl)
                volume = risk_amount / risk_per_unit if risk_per_unit > 0 else 0

                if volume > 0:
                    backtest.open_position(
                        timestamp=df.index[i],
                        price=current_price,
                        direction=direction,
                        volume=volume,
                        stop_loss=sl,
                        take_profit=tp
                    )

        # Close remaining positions
        if backtest.open_trades:
            backtest.close_all_positions(df.index[-1], df.iloc[-1]['close'])

        # Print results
        backtest.print_summary()

        # Get trades DataFrame
        trades_df = backtest.get_trades_df()
        if not trades_df.empty:
            print("\nLast 5 trades:")
            print(trades_df.tail())


async def example_indicator_calculation():
    """Example: Calculate indicators on live data"""
    print("="*60)
    print("Example: Indicator Calculation")
    print("="*60)

    from src.collector.kraken_client import KrakenClient
    from src.indicators.technical_indicators import TechnicalIndicators
    import pandas as pd

    async with KrakenClient() as client:
        # Fetch recent data
        print("Fetching recent OHLCV data...")
        result = await client.get_ohlc(pair="XBTUSD", interval=15)

        # Parse data
        ohlc_data = None
        for key, value in result.items():
            if key != "last" and isinstance(value, list):
                ohlc_data = value
                break

        if not ohlc_data:
            print("No data received")
            return

        # Convert to DataFrame
        df = pd.DataFrame(ohlc_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'vwap', 'volume', 'count'])
        df = df.astype({
            'open': 'float64',
            'high': 'float64',
            'low': 'float64',
            'close': 'float64',
            'volume': 'float64'
        })
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='s')
        df.set_index('datetime', inplace=True)

        print(f"\nLoaded {len(df)} candles (15min)")
        print(f"Latest close: ${df['close'].iloc[-1]:.2f}")

        # Calculate indicators
        indicators = TechnicalIndicators()
        signals = indicators.calculate_all_indicators(df)

        print("\nIndicator Signals:")
        print("-" * 60)

        for name, signal in signals.items():
            direction = "BUY" if signal.signal > 0 else "SELL" if signal.signal < 0 else "NEUTRAL"
            print(f"{signal.name:20s} | {direction:7s} | Signal: {signal.signal:+.2f} | Value: {signal.value:.2f}")

        print("-" * 60)


def print_menu():
    """Print example menu"""
    print("\n" + "="*60)
    print("Kraken Scalp Bot - Example Usage")
    print("="*60)
    print("1. Run in paper mode (live simulation)")
    print("2. Run backtest example")
    print("3. Calculate indicators on live data")
    print("4. Exit")
    print("="*60)


if __name__ == "__main__":
    while True:
        print_menu()
        choice = input("\nEnter your choice (1-4): ").strip()

        if choice == "1":
            asyncio.run(run_paper_mode())
        elif choice == "2":
            asyncio.run(example_backtest())
        elif choice == "3":
            asyncio.run(example_indicator_calculation())
        elif choice == "4":
            print("Exiting...")
            break
        else:
            print("Invalid choice. Please try again.")
