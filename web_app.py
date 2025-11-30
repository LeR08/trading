"""
Web Interface for Kraken Trading Bot
Modern dashboard with real-time updates
"""
import os
import json
import threading
import time
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from kraken_client import KrakenClient
from strategy import TradingStrategy
from config import Config
import logging

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Global variables
bot_running = False
bot_thread = None
kraken_client = None
strategy = None
bot_data = {
    'status': 'stopped',
    'iterations': 0,
    'trades': [],
    'current_signal': None,
    'balance': {},
    'positions': {},
    'ticker': {},
    'logs': [],
    'performance': {
        'total_pnl': 0,
        'win_rate': 0,
        'total_trades': 0
    }
}

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('WebApp')


def add_log(message, level='info'):
    """Add log message to bot data"""
    timestamp = datetime.now().strftime('%H:%M:%S')
    log_entry = {
        'time': timestamp,
        'level': level,
        'message': message
    }
    bot_data['logs'].insert(0, log_entry)
    bot_data['logs'] = bot_data['logs'][:100]  # Keep last 100 logs

    # Emit to all connected clients
    socketio.emit('log_update', log_entry)


def initialize_client(api_key=None, api_secret=None):
    """Initialize Kraken client with provided credentials"""
    global kraken_client, strategy

    try:
        if api_key and api_secret:
            kraken_client = KrakenClient(api_key, api_secret)
        else:
            kraken_client = KrakenClient()

        strategy = TradingStrategy(kraken_client)
        add_log("Kraken client initialized successfully", "success")
        return True
    except Exception as e:
        add_log(f"Failed to initialize client: {e}", "error")
        return False


def update_market_data():
    """Update market data"""
    global bot_data

    try:
        if not kraken_client:
            return

        # Get ticker
        ticker = kraken_client.get_ticker(Config.TRADING_PAIR)
        if ticker:
            bot_data['ticker'] = ticker
            socketio.emit('ticker_update', ticker)

        # Get balance
        balance = kraken_client.get_account_balance()
        if balance:
            bot_data['balance'] = balance
            socketio.emit('balance_update', balance)

        # Get positions
        positions = kraken_client.get_open_positions()
        if positions:
            bot_data['positions'] = positions
            socketio.emit('positions_update', positions)

    except Exception as e:
        add_log(f"Error updating market data: {e}", "error")


def bot_loop():
    """Main bot trading loop"""
    global bot_running, bot_data

    add_log("Trading bot started", "success")

    while bot_running:
        try:
            bot_data['iterations'] += 1

            # Update market data
            update_market_data()

            # Get current price
            ticker = bot_data.get('ticker', {})
            current_price = ticker.get('last', 0)

            if not current_price:
                add_log("Waiting for market data...", "warning")
                time.sleep(5)
                continue

            # Analyze market
            add_log(f"Analyzing market... (Iteration #{bot_data['iterations']})")
            signal_data = strategy.analyze_market()

            if signal_data:
                bot_data['current_signal'] = signal_data
                socketio.emit('signal_update', signal_data)

                # Check if should trade
                positions = bot_data.get('positions', {})
                should_trade, side, reason = strategy.should_trade(signal_data, positions)

                if should_trade:
                    add_log(f"🎯 TRADE SIGNAL: {side.upper()} - {reason}", "warning")
                    add_log(f"Signal strength: {signal_data['strength']:.1f}%", "info")

                    # Execute trade
                    success = strategy.execute_trade(side, current_price)

                    if success:
                        add_log("✅ Trade executed successfully!", "success")

                        # Record trade
                        trade = {
                            'timestamp': datetime.now().isoformat(),
                            'side': side,
                            'price': current_price,
                            'signal_strength': signal_data['strength']
                        }
                        bot_data['trades'].insert(0, trade)
                        bot_data['performance']['total_trades'] += 1

                        socketio.emit('trade_update', trade)
                    else:
                        add_log("❌ Trade execution failed", "error")
                else:
                    add_log(f"No trade: {reason}", "info")

            # Emit status update
            socketio.emit('status_update', {
                'iterations': bot_data['iterations'],
                'status': 'running'
            })

            # Wait before next iteration
            time.sleep(Config.CHECK_INTERVAL)

        except Exception as e:
            add_log(f"Error in bot loop: {e}", "error")
            logger.error(f"Bot loop error: {e}", exc_info=True)
            time.sleep(10)

    add_log("Trading bot stopped", "warning")


# Flask Routes

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('dashboard.html')


@app.route('/settings')
def settings_page():
    """Settings page"""
    return render_template('settings.html')


@app.route('/api/status')
def api_status():
    """Get bot status"""
    return jsonify({
        'running': bot_running,
        'iterations': bot_data['iterations'],
        'status': bot_data['status']
    })


@app.route('/api/data')
def api_data():
    """Get all bot data"""
    return jsonify(bot_data)


@app.route('/api/config', methods=['GET', 'POST'])
def api_config():
    """Get or update configuration"""
    if request.method == 'POST':
        data = request.json

        # Update config
        api_key = data.get('api_key')
        api_secret = data.get('api_secret')

        if api_key and api_secret:
            # Save to .env file
            env_content = f"""KRAKEN_API_KEY={api_key}
KRAKEN_API_SECRET={api_secret}

TRADING_PAIR={data.get('trading_pair', 'XXBTZUSD')}
LEVERAGE={data.get('leverage', 3)}
TAKE_PROFIT_PERCENT={data.get('take_profit', 3.0)}
STOP_LOSS_PERCENT={data.get('stop_loss', 9.0)}

CHECK_INTERVAL={data.get('check_interval', 60)}
MIN_ORDER_SIZE={data.get('min_order_size', 0.001)}
MAX_POSITION_SIZE={data.get('max_position_size', 0.1)}

MAX_DAILY_LOSS_PERCENT={data.get('max_daily_loss', 15.0)}
MAX_OPEN_POSITIONS={data.get('max_positions', 1)}
"""
            with open('.env', 'w') as f:
                f.write(env_content)

            # Reinitialize client
            initialize_client(api_key, api_secret)

            add_log("Configuration updated successfully", "success")
            return jsonify({'status': 'success', 'message': 'Configuration updated'})
        else:
            return jsonify({'status': 'error', 'message': 'API credentials required'}), 400

    # GET request - return current config
    return jsonify({
        'trading_pair': Config.TRADING_PAIR,
        'leverage': Config.LEVERAGE,
        'take_profit': Config.TAKE_PROFIT_PERCENT,
        'stop_loss': Config.STOP_LOSS_PERCENT,
        'check_interval': Config.CHECK_INTERVAL,
        'min_order_size': Config.MIN_ORDER_SIZE,
        'max_position_size': Config.MAX_POSITION_SIZE,
        'max_daily_loss': Config.MAX_DAILY_LOSS_PERCENT,
        'max_positions': Config.MAX_OPEN_POSITIONS
    })


@app.route('/api/start', methods=['POST'])
def api_start():
    """Start the trading bot"""
    global bot_running, bot_thread

    if bot_running:
        return jsonify({'status': 'error', 'message': 'Bot already running'}), 400

    if not kraken_client:
        return jsonify({'status': 'error', 'message': 'Please configure API credentials first'}), 400

    try:
        # Test API connection
        balance = kraken_client.get_account_balance()
        if not balance:
            return jsonify({'status': 'error', 'message': 'Failed to connect to Kraken API'}), 400

        # Start bot
        bot_running = True
        bot_data['status'] = 'running'
        bot_thread = threading.Thread(target=bot_loop, daemon=True)
        bot_thread.start()

        add_log("Bot started successfully", "success")
        return jsonify({'status': 'success', 'message': 'Bot started'})

    except Exception as e:
        add_log(f"Failed to start bot: {e}", "error")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/stop', methods=['POST'])
def api_stop():
    """Stop the trading bot"""
    global bot_running

    if not bot_running:
        return jsonify({'status': 'error', 'message': 'Bot not running'}), 400

    bot_running = False
    bot_data['status'] = 'stopped'
    add_log("Bot stopped by user", "warning")

    return jsonify({'status': 'success', 'message': 'Bot stopped'})


@app.route('/api/test-connection', methods=['POST'])
def api_test_connection():
    """Test Kraken API connection"""
    data = request.json
    api_key = data.get('api_key')
    api_secret = data.get('api_secret')

    if not api_key or not api_secret:
        return jsonify({'status': 'error', 'message': 'API credentials required'}), 400

    try:
        # Test connection
        test_client = KrakenClient(api_key, api_secret)
        balance = test_client.get_account_balance()
        ticker = test_client.get_ticker('XXBTZUSD')

        if balance and ticker:
            return jsonify({
                'status': 'success',
                'message': 'Connection successful',
                'balance': balance,
                'btc_price': ticker['last']
            })
        else:
            return jsonify({'status': 'error', 'message': 'Failed to fetch data'}), 400

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


# SocketIO Events

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    logger.info('Client connected')
    emit('connected', {'status': 'connected'})

    # Send current data
    emit('initial_data', bot_data)


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    logger.info('Client disconnected')


@socketio.on('request_update')
def handle_request_update():
    """Handle manual data update request"""
    update_market_data()
    emit('data_update', bot_data)


def main():
    """Run the web application"""
    print("""
╔════════════════════════════════════════════════════════════════╗
║                                                                ║
║     🚀 KRAKEN TRADING BOT - WEB INTERFACE 🚀                   ║
║                                                                ║
║  🌐 Open your browser and navigate to:                        ║
║     http://localhost:5000                                      ║
║                                                                ║
║  📊 Features:                                                  ║
║     • Real-time market data and indicators                    ║
║     • Live trading signals and analysis                       ║
║     • Configure API keys via web interface                    ║
║     • Start/Stop bot with one click                           ║
║     • Monitor positions and performance                       ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝
""")

    # Try to initialize with existing credentials
    try:
        Config.validate()
        initialize_client()
        add_log("Loaded existing API credentials", "info")
    except:
        add_log("No API credentials found. Please configure in Settings.", "warning")

    # Run the app
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)


if __name__ == '__main__':
    main()
