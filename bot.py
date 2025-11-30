"""
Professional Kraken Margin Trading Bot
Features:
- Multiple technical indicators (RSI, MACD, EMA, Bollinger Bands, Stochastic, Volume, etc.)
- 3x leverage margin trading
- Automatic TP (3%) and SL (9%)
- Risk management and position sizing
- Real-time monitoring and logging
"""
import time
import logging
from datetime import datetime
from kraken_client import KrakenClient
from strategy import TradingStrategy
from config import Config


class TradingBot:
    """Professional trading bot for Kraken margin trading"""

    def __init__(self):
        """Initialize the trading bot"""
        self.setup_logging()

        # Validate configuration
        Config.validate()

        # Initialize Kraken client
        self.client = KrakenClient()
        self.strategy = TradingStrategy(self.client)

        self.running = False
        self.iteration = 0

        self.logger.info("🤖 Trading Bot Initialized")
        self.logger.info(f"   Pair: {Config.TRADING_PAIR}")
        self.logger.info(f"   Leverage: {Config.LEVERAGE}x")
        self.logger.info(f"   Take Profit: {Config.TAKE_PROFIT_PERCENT}%")
        self.logger.info(f"   Stop Loss: {Config.STOP_LOSS_PERCENT}%")

    def setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('trading_bot.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('TradingBot')

    def display_banner(self):
        """Display bot banner"""
        banner = """
╔════════════════════════════════════════════════════════════════╗
║                                                                ║
║          🚀 KRAKEN PROFESSIONAL MARGIN TRADING BOT 🚀          ║
║                                                                ║
║  ⚡ Multi-Indicator Strategy                                   ║
║  📊 Technical Analysis: RSI, MACD, EMA, BB, Stochastic         ║
║  💰 3x Leverage Margin Trading                                 ║
║  🎯 Auto TP/SL: +3% / -9%                                      ║
║  🛡️ Advanced Risk Management                                   ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝
"""
        print(banner)

    def display_status(self, ticker, balance, positions, signal_data):
        """Display current bot status"""
        print("\n" + "="*70)
        print(f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Iteration #{self.iteration}")
        print("="*70)

        # Market Info
        print(f"\n📈 Market Data (BTC/USD):")
        print(f"   Current Price: ${ticker['last']:,.2f}")
        print(f"   24h High: ${ticker['high']:,.2f}")
        print(f"   24h Low: ${ticker['low']:,.2f}")
        print(f"   24h Volume: {ticker['volume']:,.2f} BTC")

        # Account Info
        print(f"\n💼 Account Balance:")
        for currency, amount in balance.items():
            if amount > 0:
                if currency == 'ZUSD':
                    print(f"   USD: ${amount:,.2f}")
                elif currency == 'XXBT':
                    print(f"   BTC: {amount:.6f} (${amount * ticker['last']:,.2f})")
                else:
                    print(f"   {currency}: {amount:.6f}")

        # Open Positions
        print(f"\n📊 Open Positions: {len(positions)}")
        if positions:
            for pos_id, pos in positions.items():
                pnl_pct = float(pos.get('net', 0)) * 100
                print(f"   Position: {pos['type'].upper()} | "
                      f"Size: {pos['vol']} BTC | "
                      f"P&L: {pnl_pct:+.2f}%")

        # Signal Analysis
        if signal_data:
            print(f"\n🎯 Trading Signal:")
            print(f"   Signal: {signal_data['signal'].upper()}")
            print(f"   Strength: {signal_data['strength']:.1f}%")
            print(f"   Reason: {signal_data['reason']}")

            print(f"\n📊 Key Indicators:")
            ind = signal_data['indicators']
            print(f"   RSI: {ind['rsi']:.1f} | "
                  f"MACD: {ind['macd']:.2f} | "
                  f"Stoch: {ind['stoch_k']:.1f}")
            print(f"   EMA(9): ${ind['ema_short']:,.0f} | "
                  f"EMA(21): ${ind['ema_medium']:,.0f} | "
                  f"EMA(50): ${ind['ema_long']:,.0f}")
            print(f"   BB Upper: ${ind['bb_upper']:,.0f} | "
                  f"BB Lower: ${ind['bb_lower']:,.0f}")
            print(f"   Volume Ratio: {ind['volume_ratio']:.2f}x | "
                  f"ATR: ${ind['atr']:.2f}")

        print("="*70 + "\n")

    def run_iteration(self):
        """Run one iteration of the trading bot"""
        try:
            self.iteration += 1

            # Get current market data
            ticker = self.client.get_ticker(Config.TRADING_PAIR)
            if not ticker:
                self.logger.error("Failed to fetch ticker data")
                return

            current_price = ticker['last']

            # Get account balance
            balance = self.client.get_account_balance()
            if not balance:
                self.logger.error("Failed to fetch account balance")
                return

            # Get open positions
            positions = self.client.get_open_positions()

            # Analyze market conditions
            self.logger.info("Analyzing market conditions...")
            signal_data = self.strategy.analyze_market()

            if not signal_data:
                self.logger.warning("Failed to analyze market")
                return

            # Display status
            self.display_status(ticker, balance, positions, signal_data)

            # Check if we should trade
            should_trade, side, reason = self.strategy.should_trade(
                signal_data,
                positions
            )

            if should_trade:
                self.logger.info(f"🎯 TRADE SIGNAL: {side.upper()}")
                self.logger.info(f"   Reason: {reason}")
                self.logger.info(f"   Strength: {signal_data['strength']:.1f}%")

                # Execute trade
                success = self.strategy.execute_trade(side, current_price)

                if success:
                    self.logger.info("✅ Trade executed successfully!")
                else:
                    self.logger.error("❌ Trade execution failed")
            else:
                self.logger.info(f"⏸️  No trade: {reason}")

        except Exception as e:
            self.logger.error(f"Error in iteration: {e}", exc_info=True)

    def run(self):
        """Main bot loop"""
        self.display_banner()
        self.running = True

        self.logger.info("🚀 Starting trading bot...")
        self.logger.info(f"   Check interval: {Config.CHECK_INTERVAL} seconds")

        try:
            while self.running:
                self.run_iteration()

                # Wait before next iteration
                self.logger.info(f"⏳ Waiting {Config.CHECK_INTERVAL} seconds until next check...")
                time.sleep(Config.CHECK_INTERVAL)

        except KeyboardInterrupt:
            self.logger.info("\n⚠️ Bot stopped by user")
            self.shutdown()
        except Exception as e:
            self.logger.error(f"Fatal error: {e}", exc_info=True)
            self.shutdown()

    def shutdown(self):
        """Gracefully shutdown the bot"""
        self.running = False
        self.logger.info("🛑 Shutting down bot...")

        # Display trade summary
        summary = self.strategy.get_trade_summary()
        print(summary)

        self.logger.info("👋 Bot shutdown complete")


def main():
    """Main entry point"""
    try:
        bot = TradingBot()
        bot.run()
    except Exception as e:
        print(f"Failed to start bot: {e}")
        logging.error(f"Failed to start bot: {e}", exc_info=True)


if __name__ == "__main__":
    main()
