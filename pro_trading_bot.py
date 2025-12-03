#!/usr/bin/env python3
"""
Professional Kraken Trading Bot with Position Tracking
Multi-timeframe analysis with webhook integration
"""
import time
import logging
import sys
from datetime import datetime
from kraken_client import KrakenClient
from multi_timeframe_analyzer import MultiTimeframeAnalyzer
from webhook_sender import WebhookSender
from position_tracker import PositionTracker
from config import Config


class ProTradingBot:
    """Professional trading bot with multi-timeframe analysis and position tracking"""

    def __init__(self):
        """Initialize professional bot"""
        self.setup_logging()

        self.logger.info("Initializing Professional Trading Bot...")

        # Ask for trading mode at startup
        self.paper_trading = self.ask_trading_mode()

        try:
            Config.validate()
        except ValueError as e:
            self.logger.error(f"Configuration error: {e}")
            sys.exit(1)

        self.client = KrakenClient()
        self.analyzer = MultiTimeframeAnalyzer(self.client)
        self.webhook = WebhookSender()
        self.position_tracker = PositionTracker(self.client)

        self.running = False
        self.iteration = 0
        self.last_signal_sent = None
        self.position_check_interval = 3  # Check positions every 3 iterations

        self.logger.info("Bot initialized successfully!")
        self.display_config()

    def ask_trading_mode(self):
        """Ask user for trading mode at startup"""
        print("\n" + "="*70)
        print("TRADING MODE SELECTION")
        print("="*70)
        print("\n1. 📝 PAPER TRADING (Mode Fictif - Simulation)")
        print("   - No real money at risk")
        print("   - Perfect for testing strategies")
        print("   - Simulates trades and tracks P&L")
        print("\n2. 💰 LIVE TRADING (Mode Réel)")
        print("   - REAL MONEY - REAL TRADES")
        print("   - Executes actual orders on Kraken")
        print("   - Use with caution!")

        # Check if specified in .env
        env_setting = Config.PAPER_TRADING
        print(f"\nDefault from .env: {'PAPER TRADING' if env_setting else 'LIVE TRADING'}")

        while True:
            choice = input("\nChoose mode (1=Paper, 2=Live, or press ENTER for default): ").strip()

            if choice == "":
                paper_mode = env_setting
                break
            elif choice == "1":
                paper_mode = True
                break
            elif choice == "2":
                # Confirm live trading
                confirm = input("\n⚠️  WARNING: Live trading uses REAL MONEY! Type 'CONFIRM' to proceed: ").strip()
                if confirm == "CONFIRM":
                    paper_mode = False
                    break
                else:
                    print("Live trading cancelled. Please choose again.")
            else:
                print("Invalid choice. Please enter 1, 2, or press ENTER.")

        mode_name = "PAPER TRADING (FICTIF)" if paper_mode else "LIVE TRADING (RÉEL)"
        print(f"\n✅ Mode selected: {mode_name}")
        print("="*70 + "\n")

        return paper_mode

    def setup_logging(self):
        """Setup logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('pro_trading_bot.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('ProTradingBot')

    def display_banner(self):
        """Display bot banner"""
        mode_indicator = "📝 PAPER MODE" if self.paper_trading else "💰 LIVE MODE"
        banner = f"""
╔════════════════════════════════════════════════════════════════════╗
║                                                                    ║
║       PROFESSIONAL KRAKEN MULTI-TIMEFRAME TRADING BOT             ║
║                                                                    ║
║  Multi-Timeframe Analysis (1m - 15d)                              ║
║  Weighted Confidence Score                                        ║
║  x10 Margin Trading                                               ║
║  Position Tracking & Monitoring                                   ║
║  Webhook Signal Delivery                                          ║
║  Advanced Risk Management                                         ║
║                                                                    ║
║  Mode: {mode_indicator:^54} ║
║                                                                    ║
╚════════════════════════════════════════════════════════════════════╝
"""
        print(banner)

    def display_config(self):
        """Display configuration"""
        mode_text = "PAPER TRADING (FICTIF)" if self.paper_trading else "LIVE TRADING (RÉEL)"
        print("\n" + "="*70)
        print("CONFIGURATION")
        print("="*70)
        print(f"Trading Mode: {mode_text}")
        print(f"Pair: {Config.TRADING_PAIR}")
        print(f"Leverage: {Config.LEVERAGE}x")
        print(f"Take Profit: {Config.TAKE_PROFIT_PERCENT}%")
        print(f"Stop Loss: {Config.STOP_LOSS_PERCENT}%")
        print(f"Min Confidence Score: {Config.MIN_CONFIDENCE_SCORE}%")
        print(f"Timeframes analyzed: {len(Config.TIMEFRAMES)}")
        print(f"Webhook: {Config.WEBHOOK_URL[:30]}...")
        print(f"Check interval: {Config.CHECK_INTERVAL}s")
        print("="*70 + "\n")

    def test_connections(self):
        """Test connections before starting"""
        self.logger.info("Testing connections...")

        self.logger.info("   Testing Kraken API...")
        ticker = self.client.get_ticker(Config.TRADING_PAIR)
        if ticker:
            self.logger.info(f"   Kraken API OK - BTC Price: ${ticker['last']:,.2f}")
        else:
            self.logger.error("   Kraken API inaccessible")
            return False

        self.logger.info("   Testing Webhook...")
        if self.webhook.test_webhook():
            self.logger.info("   Webhook OK")
        else:
            self.logger.error("   Webhook inaccessible")
            return False

        self.logger.info("All tests passed!\n")

        # Send startup notification
        mode_text = "PAPER TRADING" if self.paper_trading else "LIVE TRADING"
        self.webhook.send_alert('INFO', f'Bot started in {mode_text} mode')

        return True

    def check_and_display_positions(self, current_price):
        """Check and display position status"""
        try:
            if self.paper_trading:
                status = self.position_tracker.get_paper_positions_status(current_price)
            else:
                status = self.position_tracker.get_positions_status(current_price)

            # Display in console
            self.position_tracker.display_positions(status)

            # Send to webhook if there are positions
            if status['total_positions'] > 0:
                self.webhook.send_position_status(status, self.paper_trading)

            return status

        except Exception as e:
            self.logger.error(f"Error checking positions: {e}")
            return None

    def run_analysis(self):
        """Run complete analysis"""
        try:
            self.iteration += 1

            self.logger.info(f"\n{'='*70}")
            self.logger.info(f"ITERATION #{self.iteration} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            mode_text = "PAPER TRADING" if self.paper_trading else "LIVE TRADING"
            self.logger.info(f"Mode: {mode_text}")
            self.logger.info(f"{'='*70}\n")

            ticker = self.client.get_ticker(Config.TRADING_PAIR)
            if not ticker:
                self.logger.error("Cannot get current price")
                return

            current_price = ticker['last']
            self.logger.info(f"Current BTC/USD Price: ${current_price:,.2f}")

            balance = self.client.get_account_balance()
            if balance:
                usd_balance = balance.get('ZUSD', 0)
                btc_balance = balance.get('XXBT', 0)
                self.logger.info(f"Balance: ${usd_balance:,.2f} USD | {btc_balance:.6f} BTC")

            # Check positions status every N iterations
            if self.iteration % self.position_check_interval == 0:
                self.check_and_display_positions(current_price)

            self.logger.info("\nStarting multi-timeframe analysis...\n")
            analysis = self.analyzer.get_comprehensive_analysis(Config.TRADING_PAIR)

            self.analyzer.display_analysis_summary(analysis)

            if analysis['should_trade'] and analysis['action'] != 'HOLD':
                self.logger.info(f"TRADING SIGNAL DETECTED!")
                self.logger.info(f"   Action: {analysis['action']}")
                self.logger.info(f"   Confidence: {analysis['confidence_score']}%")

                signal_data = self._prepare_signal_data(analysis, balance, current_price)
                self.send_trading_signal(signal_data)

                # Execute trade based on mode
                if self.paper_trading:
                    self.execute_paper_trade(signal_data)
                else:
                    # In live mode, send signal but DON'T execute automatically
                    # User needs to uncomment execute_trade() call to enable
                    self.logger.info("⚠️  Live trade signal ready (auto-execution disabled)")
                    # Uncomment line below to enable automatic live trading:
                    # self.execute_trade(signal_data)

            else:
                reason = "Insufficient confidence" if analysis['confidence_score'] < Config.MIN_CONFIDENCE_SCORE else "No clear signal"
                self.logger.info(f"No trade: {reason}")

            self.logger.info(f"\n{'='*70}\n")

        except Exception as e:
            self.logger.error(f"Error during analysis: {e}", exc_info=True)

    def _prepare_signal_data(self, analysis, balance, current_price):
        """Prepare signal data for webhook"""
        usd_balance = balance.get('ZUSD', 0) if balance else 0
        position_size = self._calculate_position_size(usd_balance, current_price)

        signal_data = {
            'action': analysis['action'],
            'pair': analysis['pair'].replace('XXBTZUSD', 'BTC/USD'),
            'leverage': analysis['leverage'],
            'entry_price': analysis['entry_price'],
            'take_profit': analysis['take_profit'],
            'stop_loss': analysis['stop_loss'],
            'tp_percent': analysis['tp_percent'],
            'sl_percent': analysis['sl_percent'],
            'confidence_score': analysis['confidence_score'],
            'position_size': position_size,
            'timeframe_analysis': analysis['timeframe_analysis'],
            'reason': analysis['reason'],
            'indicators': analysis.get('indicators', {}),
            'market_conditions': {
                'current_price': current_price,
                'account_balance_usd': usd_balance,
                '24h_high': 0,
                '24h_low': 0,
                '24h_volume': 0
            }
        }

        return signal_data

    def _calculate_position_size(self, usd_balance, current_price):
        """Calculate position size based on risk"""
        if usd_balance < 100:
            return Config.MIN_ORDER_SIZE

        risk_amount = usd_balance * 0.02
        stop_loss_decimal = Config.STOP_LOSS_PERCENT / 100
        position_value = risk_amount / stop_loss_decimal
        position_value = position_value * Config.LEVERAGE
        position_size_btc = position_value / current_price

        position_size_btc = max(Config.MIN_ORDER_SIZE, position_size_btc)
        position_size_btc = min(Config.MAX_POSITION_SIZE, position_size_btc)

        return round(position_size_btc, 4)

    def send_trading_signal(self, signal_data):
        """Send trading signal via webhook"""
        try:
            mode_text = "PAPER TRADING" if self.paper_trading else "LIVE TRADING"
            self.logger.info(f"\nSENDING TRADING SIGNAL VIA WEBHOOK ({mode_text})")
            self.logger.info("="*70)

            success = self.webhook.send_trading_signal(signal_data)

            if success:
                self.logger.info("Signal sent successfully!")
                self.last_signal_sent = {
                    'timestamp': datetime.now(),
                    'action': signal_data['action'],
                    'confidence': signal_data['confidence_score']
                }

                self._display_signal_details(signal_data)

            else:
                self.logger.error("Failed to send signal")

            self.logger.info("="*70 + "\n")

        except Exception as e:
            self.logger.error(f"Error sending signal: {e}", exc_info=True)

    def _display_signal_details(self, signal_data):
        """Display sent signal details"""
        mode_text = "PAPER" if self.paper_trading else "LIVE"
        print(f"\nSIGNAL DETAILS SENT ({mode_text}):")
        print(f"   Action: {signal_data['action']}")
        print(f"   Pair: {signal_data['pair']}")
        print(f"   Leverage: {signal_data['leverage']}x")
        print(f"   Size: {signal_data['position_size']} BTC")
        print(f"   Entry: ${signal_data['entry_price']:,.2f}")
        print(f"   TP: ${signal_data['take_profit']:,.2f} (+{signal_data['tp_percent']}%)")
        print(f"   SL: ${signal_data['stop_loss']:,.2f} (-{signal_data['sl_percent']}%)")
        print(f"   Confidence: {signal_data['confidence_score']}%")
        print(f"   Reason: {signal_data['reason']}")

    def execute_paper_trade(self, signal_data):
        """Execute paper trade (simulation)"""
        try:
            self.logger.info("\n📝 EXECUTING PAPER TRADE (SIMULATION)")

            position = self.position_tracker.add_paper_position(
                side=signal_data['action'],
                volume=signal_data['position_size'],
                entry_price=signal_data['entry_price'],
                leverage=signal_data['leverage'],
                tp=signal_data['take_profit'],
                sl=signal_data['stop_loss']
            )

            self.logger.info(f"✅ Paper position opened: {position['id']}")
            self.webhook.send_alert(
                'SUCCESS',
                f"Paper trade executed: {signal_data['action']} {signal_data['position_size']} BTC",
                {'position_id': position['id']}
            )

        except Exception as e:
            self.logger.error(f"Error executing paper trade: {e}", exc_info=True)

    def execute_trade(self, signal_data):
        """
        Execute REAL trade (LIVE TRADING)
        WARNING: This places real orders with real money!
        """
        self.logger.warning("\n💰 AUTOMATIC LIVE TRADE EXECUTION")
        self.logger.warning("⚠️  This will place a REAL order with REAL MONEY!")

        try:
            side = signal_data['action'].lower()
            volume = signal_data['position_size']
            entry_price = signal_data['entry_price']

            self.logger.info(f"Placing {side.upper()} order...")
            self.logger.info(f"   Volume: {volume} BTC")
            self.logger.info(f"   Leverage: {Config.LEVERAGE}x")

            result = self.client.place_market_order_with_sltp(
                side=side,
                volume=volume,
                entry_price=entry_price,
                pair=Config.TRADING_PAIR,
                leverage=Config.LEVERAGE
            )

            if result:
                self.logger.info("✅ Order placed successfully!")
                self.logger.info(f"   Transaction ID: {result.get('txid', [])}")

                self.webhook.send_alert(
                    'SUCCESS',
                    f"LIVE Order {side.upper()} executed successfully",
                    {'txid': result.get('txid', []), 'volume': volume}
                )

            else:
                self.logger.error("❌ Order placement failed")
                self.webhook.send_alert('ERROR', 'Live order placement failed')

        except Exception as e:
            self.logger.error(f"Error executing live trade: {e}", exc_info=True)
            self.webhook.send_alert('ERROR', f'Live trade error: {str(e)}')

    def run(self):
        """Main bot loop"""
        self.display_banner()

        if not self.test_connections():
            self.logger.error("Connection tests failed. Stopping bot.")
            sys.exit(1)

        self.running = True
        mode_text = "PAPER TRADING" if self.paper_trading else "LIVE TRADING"
        self.logger.info(f"Bot started in {mode_text} mode!\n")

        try:
            while self.running:
                self.run_analysis()

                self.logger.info(f"Waiting {Config.CHECK_INTERVAL} seconds before next analysis...\n")
                time.sleep(Config.CHECK_INTERVAL)

        except KeyboardInterrupt:
            self.logger.info("\nBot stopped by user")
            self.shutdown()
        except Exception as e:
            self.logger.error(f"Fatal error: {e}", exc_info=True)
            self.webhook.send_alert('ERROR', f'Fatal bot error: {str(e)}')
            self.shutdown()

    def shutdown(self):
        """Shutdown bot gracefully"""
        self.running = False
        self.logger.info("\nStopping bot...")

        mode_text = "PAPER TRADING" if self.paper_trading else "LIVE TRADING"
        self.webhook.send_alert('INFO', f'Trading bot stopped ({mode_text} mode)')

        if self.last_signal_sent:
            print("\nLAST SIGNAL SENT:")
            print(f"   Timestamp: {self.last_signal_sent['timestamp']}")
            print(f"   Action: {self.last_signal_sent['action']}")
            print(f"   Confidence: {self.last_signal_sent['confidence']}%")

        self.logger.info("Bot stopped. Goodbye!")


def main():
    """Main entry point"""
    try:
        bot = ProTradingBot()
        bot.run()
    except Exception as e:
        print(f"Fatal error on startup: {e}")
        logging.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
