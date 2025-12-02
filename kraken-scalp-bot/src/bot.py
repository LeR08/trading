"""
Kraken Scalp Bot - Main orchestrator

Coordinates all modules:
- Data collection
- Indicator calculation
- Signal generation
- Risk management
- Order execution
"""
import asyncio
import signal
import sys
from datetime import datetime, timezone
from typing import Dict, Optional
import logging

from .collector.kraken_client import KrakenClient
from .collector.ohlcv_collector import OHLCVCollector
from .indicators.technical_indicators import TechnicalIndicators
from .signal_engine.signal_generator import SignalGenerator, Direction
from .risk_engine.risk_manager import RiskManager, PositionSize
from .executor.order_executor import OrderExecutor, ExecutionMode
from .monitoring.metrics import BotMetrics, start_metrics_server
from .utils.config import Config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class KrakenScalpBot:
    """
    Main bot orchestrator

    Workflow:
    1. Fetch OHLCV data (every 40s)
    2. Calculate indicators
    3. Generate signals
    4. Check risk constraints
    5. Execute trades if conditions met
    """

    def __init__(self, config_path: str = "config/config.yaml"):
        """
        Initialize bot

        Args:
            config_path: Path to configuration file
        """
        logger.info("Initializing Kraken Scalp Bot...")

        # Load configuration
        self.config = Config(config_path)
        if not self.config.validate():
            raise ValueError("Invalid configuration")

        # Initialize Kraken client
        api_key = self.config.kraken_api_key if self.config.execution_mode != "paper" else None
        api_secret = self.config.kraken_api_secret if self.config.execution_mode != "paper" else None

        self.client = KrakenClient(api_key=api_key, api_secret=api_secret)

        # Initialize modules
        self.collector = OHLCVCollector(
            client=self.client,
            pair=self.config.trading_pair,
            timeframes=self.config.timeframes,
            use_partial_candle=self.config.get("trading.use_partial_candle", True)
        )

        self.indicators = TechnicalIndicators()

        self.signal_generator = SignalGenerator(
            weights=self.config.indicator_weights,
            confidence_threshold=self.config.confidence_threshold
        )

        self.risk_manager = RiskManager(
            risk_per_trade=self.config.risk_per_trade,
            max_total_exposure=self.config.get("risk.max_total_exposure", 0.05),
            leverage=self.config.leverage,
            max_daily_drawdown=self.config.get("risk.max_daily_drawdown", 0.03),
            max_total_drawdown=self.config.get("risk.max_total_drawdown", 0.10),
            max_concurrent_trades=self.config.get("risk.max_concurrent_trades", 3)
        )

        # Map execution mode
        mode_map = {
            "paper": ExecutionMode.PAPER,
            "validate": ExecutionMode.VALIDATE,
            "live": ExecutionMode.LIVE
        }
        exec_mode = mode_map.get(self.config.execution_mode, ExecutionMode.PAPER)

        self.executor = OrderExecutor(
            client=self.client,
            mode=exec_mode,
            max_retries=self.config.get("execution.max_retries", 3),
            retry_delay=self.config.get("execution.retry_delay", 2.0)
        )

        # Metrics
        self.metrics = BotMetrics()

        # State
        self.running = False
        self.iteration = 0

        logger.info(f"Bot initialized in {exec_mode.value} mode")
        logger.info(f"Trading pair: {self.config.trading_pair}")
        logger.info(f"Leverage: {self.config.leverage}x")
        logger.info(f"Timeframes: {self.config.timeframes}")
        logger.info(f"Confidence threshold: {self.config.confidence_threshold*100}%")

    async def initialize(self):
        """Initialize bot - fetch historical data"""
        logger.info("Initializing bot...")

        # Note: client session is managed by run() method
        # Verify asset pair configuration
        asset_pairs = await self.client.get_asset_pairs(self.config.trading_pair)
        logger.info(f"Asset pair info: {asset_pairs}")

        # Initialize data collector
        lookback = self.config.get("data.lookback_periods", 200)
        await self.collector.initialize(lookback_periods=lookback)

        logger.info("Bot initialization complete")

    async def run_iteration(self):
        """Run a single bot iteration"""
        self.iteration += 1
        logger.info(f"\n{'='*60}")
        logger.info(f"ITERATION {self.iteration} - {datetime.now(timezone.utc).isoformat()}")
        logger.info(f"{'='*60}")

        try:
            # 1. Fetch OHLCV data
            logger.info("Fetching OHLCV data...")
            data = await self.collector.fetch_all_timeframes()

            # 2. Calculate indicators for each timeframe
            logger.info("Calculating indicators...")
            timeframe_signals = {}

            for tf, (df, partial_candle) in data.items():
                if df.empty:
                    logger.warning(f"No data for {tf}m")
                    continue

                # Calculate indicators
                signals = self.indicators.calculate_all_indicators(df)

                if not signals:
                    logger.warning(f"No indicators calculated for {tf}m")
                    continue

                # Generate trading signal
                timestamp = int(datetime.now(timezone.utc).timestamp())
                trading_signal = self.signal_generator.generate_signal(signals, tf, timestamp)

                timeframe_signals[tf] = trading_signal

                # Update metrics
                direction_value = 1 if trading_signal.direction == Direction.LONG else -1 if trading_signal.direction == Direction.SHORT else 0
                self.metrics.update_signal(tf, trading_signal.confidence, direction_value)

                logger.info(
                    f"[{tf}m] Signal: {trading_signal.direction.value} | "
                    f"Confidence: {trading_signal.confidence:.2f}% | "
                    f"Bullish: {trading_signal.metadata['bullish_count']} | "
                    f"Bearish: {trading_signal.metadata['bearish_count']}"
                )

            # 3. Combine signals from multiple timeframes
            if not timeframe_signals:
                logger.warning("No valid signals generated")
                return

            primary_tf = min(self.config.timeframes)  # Use smallest timeframe as primary
            combined_signal = self.signal_generator.combine_timeframes(timeframe_signals, primary_tf)

            if not combined_signal or combined_signal.direction == Direction.NEUTRAL:
                logger.info("No actionable signal (neutral or low confidence)")
                return

            logger.info(f"✓ Combined signal: {combined_signal.direction.value} with {combined_signal.confidence:.2f}% confidence")

            # 4. Check if we should open a trade
            if combined_signal.confidence < self.config.confidence_threshold * 100:
                logger.info(f"Signal below threshold ({combined_signal.confidence:.2f}% < {self.config.confidence_threshold*100}%)")
                return

            # 5. Get current price and ATR for SL/TP calculation
            current_price = await self.collector.get_current_price()
            if not current_price:
                logger.error("Could not get current price")
                return

            logger.info(f"Current price: ${current_price:.2f}")

            # Get ATR from primary timeframe
            primary_df = self.collector.get_latest_data(primary_tf, limit=50)
            atr = self.indicators.calculate_atr(primary_df, 14).iloc[-1]

            # 6. Calculate stop loss and take profit
            direction_str = "long" if combined_signal.direction == Direction.LONG else "short"
            sl_multiplier = self.config.get("risk.sl_atr_multiplier", 1.0)
            tp_ratio = self.config.get("risk.tp_reward_ratio", 0.7)

            stop_loss = self.risk_manager.calculate_stop_loss(current_price, atr, direction_str, sl_multiplier)
            take_profit = self.risk_manager.calculate_take_profit(current_price, stop_loss, direction_str, tp_ratio)

            logger.info(f"Stop Loss: ${stop_loss:.2f} | Take Profit: ${take_profit:.2f}")

            # 7. Get trade balance and calculate position size
            trade_balance = await self.client.get_trade_balance()
            equity = float(trade_balance.get("e", 0))

            logger.info(f"Current equity: ${equity:.2f}")

            # Calculate position size
            position_size = self.risk_manager.calculate_position_size(
                equity=equity,
                entry_price=current_price,
                stop_loss_price=stop_loss,
                take_profit_price=take_profit,
                direction=direction_str,
                pair_decimals=8  # BTC has 8 decimals
            )

            logger.info(
                f"Position size: {position_size.volume:.8f} BTC "
                f"(${position_size.notional_value:.2f} notional, "
                f"${position_size.margin_required:.2f} margin)"
            )

            # 8. Perform risk checks
            open_orders = await self.executor.get_open_orders()

            risk_check = self.risk_manager.perform_full_risk_check(
                position_size=position_size,
                trade_balance=trade_balance,
                current_open_positions=open_orders
            )

            if not risk_check.approved:
                logger.warning(f"Risk check REJECTED: {risk_check.reason}")
                return

            if risk_check.warnings:
                for warning in risk_check.warnings:
                    logger.warning(f"Risk warning: {warning}")

            logger.info("✓ All risk checks passed")

            # 9. Execute trade
            logger.info(f"Executing {direction_str} order...")

            use_limit = self.config.get("execution.use_limit_orders", True)

            if use_limit:
                # Place limit order slightly better than current price
                offset_pct = self.config.get("execution.limit_order_offset_pct", 0.0005)
                if direction_str == "long":
                    limit_price = current_price * (1 - offset_pct)
                else:
                    limit_price = current_price * (1 + offset_pct)

                result = await self.executor.place_limit_order(
                    pair=self.config.trading_pair,
                    direction=direction_str,
                    volume=position_size.volume,
                    price=limit_price,
                    leverage=self.config.leverage,
                    stop_loss=stop_loss,
                    take_profit=take_profit
                )
            else:
                result = await self.executor.place_market_order(
                    pair=self.config.trading_pair,
                    direction=direction_str,
                    volume=position_size.volume,
                    leverage=self.config.leverage,
                    stop_loss=stop_loss,
                    take_profit=take_profit
                )

            if result.success:
                logger.info(f"✓ Order placed successfully: {result.order_id}")
                logger.info(f"  Direction: {direction_str}")
                logger.info(f"  Volume: {position_size.volume:.8f} BTC")
                logger.info(f"  Entry: ${current_price:.2f}")
                logger.info(f"  SL: ${stop_loss:.2f} | TP: ${take_profit:.2f}")
                logger.info(f"  Risk: ${position_size.risk_amount:.2f} | Reward: ${position_size.reward_amount:.2f}")
            else:
                logger.error(f"✗ Order failed: {result.message}")
                self.metrics.record_error("order_execution")

        except Exception as e:
            logger.error(f"Error in iteration: {e}", exc_info=True)
            self.metrics.record_error("iteration")

    async def run(self):
        """Main bot loop"""
        self.running = True

        # Start metrics server
        if self.config.get("monitoring.enable_metrics", True):
            metrics_port = self.config.get("monitoring.metrics_port", 8000)
            start_metrics_server(metrics_port)

        async with self.client:
            # Initialize
            await self.initialize()

            # Main loop
            refresh_interval = self.config.refresh_interval

            logger.info(f"\nStarting main loop (refresh every {refresh_interval}s)...")

            while self.running:
                try:
                    await self.run_iteration()

                    # Wait for next iteration
                    await asyncio.sleep(refresh_interval)

                except KeyboardInterrupt:
                    logger.info("\nShutdown requested...")
                    break
                except Exception as e:
                    logger.error(f"Critical error: {e}", exc_info=True)
                    await asyncio.sleep(refresh_interval)

        logger.info("Bot stopped")

    def stop(self):
        """Stop the bot"""
        logger.info("Stopping bot...")
        self.running = False


async def main():
    """Main entry point"""
    bot = KrakenScalpBot()

    # Handle shutdown signals
    def signal_handler(sig, frame):
        logger.info(f"\nReceived signal {sig}")
        bot.stop()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        await bot.run()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
