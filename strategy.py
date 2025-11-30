"""
Professional Trading Strategy with Risk Management
"""
import pandas as pd
from datetime import datetime, timedelta
from indicators import TechnicalIndicators
from kraken_client import KrakenClient
from config import Config


class TradingStrategy:
    """Professional trading strategy combining multiple indicators"""

    def __init__(self, kraken_client):
        """Initialize trading strategy"""
        self.client = kraken_client
        self.trade_history = []
        self.daily_pnl = 0
        self.last_reset = datetime.now().date()

    def should_trade(self, signal_data, current_positions):
        """
        Determine if we should execute a trade based on signals and risk management
        Returns: (should_trade, side, reason)
        """
        # Check if we already have max open positions
        if len(current_positions) >= Config.MAX_OPEN_POSITIONS:
            return False, None, "Maximum open positions reached"

        # Check daily loss limit
        if self._check_daily_loss_limit():
            return False, None, f"Daily loss limit exceeded ({Config.MAX_DAILY_LOSS_PERCENT}%)"

        # Get signal
        signal = signal_data['signal']
        strength = signal_data['strength']

        # Need strong signal (>60%) to trade
        if signal == 'hold' or strength < 60:
            return False, None, f"Signal too weak (strength: {strength}%)"

        # Check if we already have a position in the same direction
        for pos_id, pos_data in current_positions.items():
            if pos_data['type'] == signal:
                return False, None, f"Already have open {signal} position"

        # All checks passed
        return True, signal, signal_data['reason']

    def calculate_position_size(self, balance, current_price, leverage=3):
        """
        Calculate optimal position size based on risk management
        Uses Kelly Criterion modified for crypto trading
        """
        try:
            # Get USD balance
            usd_balance = balance.get('ZUSD', 0)

            if usd_balance < 100:
                print(f"⚠️ Insufficient balance: ${usd_balance:.2f}")
                return 0

            # Risk per trade: 2% of balance
            risk_amount = usd_balance * 0.02

            # Calculate position size based on stop loss
            stop_loss_decimal = Config.STOP_LOSS_PERCENT / 100
            position_value = risk_amount / stop_loss_decimal

            # Apply leverage
            position_value = position_value * leverage

            # Convert to BTC
            position_size_btc = position_value / current_price

            # Apply limits
            position_size_btc = max(Config.MIN_ORDER_SIZE, position_size_btc)
            position_size_btc = min(Config.MAX_POSITION_SIZE, position_size_btc)

            # Round to 4 decimals
            position_size_btc = round(position_size_btc, 4)

            print(f"\n💰 Position Sizing:")
            print(f"  Account Balance: ${usd_balance:,.2f}")
            print(f"  Risk per Trade: ${risk_amount:,.2f} (2%)")
            print(f"  Position Size: {position_size_btc} BTC")
            print(f"  Position Value: ${position_value:,.2f}")
            print(f"  Leverage: {leverage}x")

            return position_size_btc

        except Exception as e:
            print(f"Error calculating position size: {e}")
            return Config.MIN_ORDER_SIZE

    def execute_trade(self, side, entry_price):
        """Execute a trade with proper risk management"""
        try:
            # Get account balance
            balance = self.client.get_account_balance()
            if not balance:
                print("❌ Failed to get account balance")
                return False

            # Calculate position size
            position_size = self.calculate_position_size(
                balance,
                entry_price,
                leverage=Config.LEVERAGE
            )

            if position_size < Config.MIN_ORDER_SIZE:
                print(f"❌ Position size too small: {position_size} BTC")
                return False

            # Place order with SL/TP
            print(f"\n🚀 Executing {side.upper()} trade...")
            result = self.client.place_market_order_with_sltp(
                side=side,
                volume=position_size,
                entry_price=entry_price,
                pair=Config.TRADING_PAIR,
                leverage=Config.LEVERAGE
            )

            if result:
                print(f"✅ Order placed successfully!")
                print(f"   Transaction IDs: {result.get('txid', [])}")

                # Record trade
                self.trade_history.append({
                    'timestamp': datetime.now(),
                    'side': side,
                    'size': position_size,
                    'entry_price': entry_price,
                    'leverage': Config.LEVERAGE,
                    'txid': result.get('txid', [])
                })

                return True
            else:
                print("❌ Order placement failed")
                return False

        except Exception as e:
            print(f"❌ Error executing trade: {e}")
            return False

    def _check_daily_loss_limit(self):
        """Check if daily loss limit has been exceeded"""
        today = datetime.now().date()

        # Reset daily P&L if it's a new day
        if today != self.last_reset:
            self.daily_pnl = 0
            self.last_reset = today

        # Check if loss limit exceeded
        return self.daily_pnl < -(Config.MAX_DAILY_LOSS_PERCENT / 100)

    def update_daily_pnl(self, pnl):
        """Update daily P&L"""
        self.daily_pnl += pnl

    def analyze_market(self, lookback_candles=100):
        """
        Analyze market conditions using technical indicators
        Returns: signal data with recommendation
        """
        try:
            # Fetch OHLC data (60-minute candles)
            df = self.client.get_ohlc_data(
                pair=Config.TRADING_PAIR,
                interval=60  # 1-hour candles
            )

            if df is None or len(df) < lookback_candles:
                print("⚠️ Insufficient data for analysis")
                return None

            # Use last N candles
            df = df.tail(lookback_candles)

            # Calculate all technical indicators
            indicators = TechnicalIndicators(df)
            df_with_indicators = indicators.calculate_all()

            # Get trading signals
            signal_data = indicators.get_trading_signals()

            return signal_data

        except Exception as e:
            print(f"Error analyzing market: {e}")
            return None

    def get_trade_summary(self):
        """Get summary of recent trades"""
        if not self.trade_history:
            return "No trades executed yet"

        summary = f"\n📊 Trade Summary (Last {len(self.trade_history)} trades):\n"
        summary += "=" * 60 + "\n"

        for i, trade in enumerate(self.trade_history[-10:], 1):
            summary += f"{i}. {trade['timestamp'].strftime('%Y-%m-%d %H:%M:%S')} - "
            summary += f"{trade['side'].upper()} {trade['size']} BTC @ ${trade['entry_price']:,.2f} "
            summary += f"(Leverage: {trade['leverage']}x)\n"

        summary += "=" * 60

        return summary
