"""
Demo Web Interface for Kraken Trading Bot
Works without Kraken API - Shows interface only
"""
import os
import json
import time
import random
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import logging

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Demo data
demo_data = {
    'status': 'demo',
    'iterations': 0,
    'trades': [],
    'current_signal': {
        'signal': 'hold',
        'strength': 45.0,
        'reason': 'MODE DEMO - Pas de connexion Kraken. Configurez vos clés API dans Settings.',
        'indicators': {
            'rsi': 52.3,
            'macd': 45.67,
            'macd_signal': 43.21,
            'ema_short': 96500,
            'ema_medium': 95800,
            'ema_long': 94200,
            'bb_upper': 99000,
            'bb_lower': 94000,
            'stoch_k': 48.5,
            'volume_ratio': 1.2,
            'atr': 1250.0
        }
    },
    'balance': {
        'ZUSD': 10000.0,
        'XXBT': 0.0
    },
    'positions': {},
    'ticker': {
        'last': 97234.50,
        'high': 98150.00,
        'low': 95800.00,
        'volume': 1234.56
    },
    'logs': []
}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('WebDemo')


def add_log(message, level='info'):
    """Add log message"""
    timestamp = datetime.now().strftime('%H:%M:%S')
    log_entry = {
        'time': timestamp,
        'level': level,
        'message': message
    }
    demo_data['logs'].insert(0, log_entry)
    demo_data['logs'] = demo_data['logs'][:100]
    socketio.emit('log_update', log_entry)


def update_demo_data():
    """Update demo data with random variations"""
    # Update price
    price_change = random.uniform(-500, 500)
    demo_data['ticker']['last'] = max(90000, min(105000, demo_data['ticker']['last'] + price_change))

    # Update indicators
    demo_data['current_signal']['indicators']['rsi'] = max(0, min(100, demo_data['current_signal']['indicators']['rsi'] + random.uniform(-5, 5)))
    demo_data['current_signal']['indicators']['macd'] = demo_data['current_signal']['indicators']['macd'] + random.uniform(-10, 10)

    # Random signal
    signals = ['buy', 'sell', 'hold']
    weights = [0.2, 0.2, 0.6]
    demo_data['current_signal']['signal'] = random.choices(signals, weights)[0]
    demo_data['current_signal']['strength'] = random.uniform(30, 85)


# Flask Routes
@app.route('/')
def index():
    return render_template('dashboard.html')


@app.route('/settings')
def settings_page():
    return render_template('settings.html')


@app.route('/api/status')
def api_status():
    return jsonify({
        'running': False,
        'iterations': demo_data['iterations'],
        'status': 'demo'
    })


@app.route('/api/data')
def api_data():
    return jsonify(demo_data)


@app.route('/api/config', methods=['GET', 'POST'])
def api_config():
    if request.method == 'POST':
        data = request.json
        api_key = data.get('api_key')
        api_secret = data.get('api_secret')

        if api_key and api_secret:
            # Save to .env
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

            add_log("Configuration sauvegardée. Redémarrez avec web_app.py pour utiliser l'API réelle.", "success")
            return jsonify({
                'status': 'success',
                'message': 'Configuration saved. Restart with web_app.py to use real Kraken API'
            })

        return jsonify({'status': 'error', 'message': 'API credentials required'}), 400

    return jsonify({
        'trading_pair': 'XXBTZUSD',
        'leverage': 3,
        'take_profit': 3.0,
        'stop_loss': 9.0,
        'check_interval': 60,
        'min_order_size': 0.001,
        'max_position_size': 0.1,
        'max_daily_loss': 15.0,
        'max_positions': 1
    })


@app.route('/api/start', methods=['POST'])
def api_start():
    add_log("MODE DEMO - Installez les packages Kraken pour activer le trading réel", "warning")
    return jsonify({
        'status': 'error',
        'message': 'Mode démo - Installez krakenex pour le trading réel'
    }), 400


@app.route('/api/stop', methods=['POST'])
def api_stop():
    return jsonify({'status': 'success', 'message': 'Bot stopped'})


@app.route('/api/test-connection', methods=['POST'])
def api_test_connection():
    data = request.json
    api_key = data.get('api_key')
    api_secret = data.get('api_secret')

    if not api_key or not api_secret:
        return jsonify({'status': 'error', 'message': 'API credentials required'}), 400

    # Demo mode - just save credentials
    add_log(f"Clés API sauvegardées (mode démo)", "info")

    return jsonify({
        'status': 'warning',
        'message': 'Mode démo - Credentials saved. Install krakenex package for real API test',
        'balance': demo_data['balance'],
        'btc_price': demo_data['ticker']['last']
    })


# SocketIO Events
@socketio.on('connect')
def handle_connect():
    logger.info('Client connected')
    emit('connected', {'status': 'connected'})
    add_log("Connecté en MODE DEMO. Installez krakenex pour le trading réel.", "warning")
    emit('initial_data', demo_data)


@socketio.on('disconnect')
def handle_disconnect():
    logger.info('Client disconnected')


@socketio.on('request_update')
def handle_request_update():
    update_demo_data()
    emit('data_update', demo_data)


def main():
    """Run the demo web application"""
    print("""
╔════════════════════════════════════════════════════════════════╗
║                                                                ║
║        🚀 KRAKEN TRADING BOT - WEB DEMO MODE 🚀                ║
║                                                                ║
║  🌐 Open your browser and navigate to:                        ║
║     http://localhost:5000                                      ║
║                                                                ║
║  📊 Demo Mode Features:                                        ║
║     • Full web interface                                      ║
║     • Simulated market data                                   ║
║     • Configure API keys                                      ║
║     • Test the interface                                      ║
║                                                                ║
║  ⚠️  Note: This is DEMO MODE                                   ║
║     Install krakenex package for real trading                 ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝
""")

    add_log("Interface web démarrée en MODE DEMO", "info")
    add_log("Ouvrez http://localhost:5000 dans votre navigateur", "success")
    add_log("Pour activer le trading réel, installez: pip install krakenex ta", "warning")

    # Run the app
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)


if __name__ == '__main__':
    main()
