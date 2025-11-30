"""
Kraken API Client for Margin Trading
"""
import krakenex
import time
import hashlib
import hmac
import base64
import urllib.parse
import requests
import pandas as pd
from datetime import datetime
from config import Config


class KrakenClient:
    """Kraken API client with margin trading support"""

    def __init__(self, api_key=None, api_secret=None):
        """Initialize Kraken client"""
        self.api_key = api_key or Config.KRAKEN_API_KEY
        self.api_secret = api_secret or Config.KRAKEN_API_SECRET

        self.api = krakenex.API()
        self.api.key = self.api_key
        self.api.secret = self.api_secret

        self.base_url = "https://api.kraken.com"

    def get_ohlc_data(self, pair='XXBTZUSD', interval=60, since=None):
        """
        Get OHLC (candlestick) data
        interval: in minutes (1, 5, 15, 30, 60, 240, 1440, 10080, 21600)
        """
        try:
            params = {
                'pair': pair,
                'interval': interval
            }
            if since:
                params['since'] = since

            response = self.api.query_public('OHLC', params)

            if response.get('error'):
                raise Exception(f"Kraken API error: {response['error']}")

            # Convert to DataFrame
            ohlc_data = response['result'][pair]
            df = pd.DataFrame(ohlc_data, columns=[
                'time', 'open', 'high', 'low', 'close', 'vwap', 'volume', 'count'
            ])

            # Convert types
            df['time'] = pd.to_datetime(df['time'], unit='s')
            for col in ['open', 'high', 'low', 'close', 'vwap', 'volume']:
                df[col] = df[col].astype(float)

            return df

        except Exception as e:
            print(f"Error fetching OHLC data: {e}")
            return None

    def get_ticker(self, pair='XXBTZUSD'):
        """Get current ticker information"""
        try:
            response = self.api.query_public('Ticker', {'pair': pair})

            if response.get('error'):
                raise Exception(f"Kraken API error: {response['error']}")

            ticker = response['result'][pair]
            return {
                'ask': float(ticker['a'][0]),
                'bid': float(ticker['b'][0]),
                'last': float(ticker['c'][0]),
                'volume': float(ticker['v'][1]),
                'vwap': float(ticker['p'][1]),
                'high': float(ticker['h'][1]),
                'low': float(ticker['l'][1])
            }

        except Exception as e:
            print(f"Error fetching ticker: {e}")
            return None

    def get_account_balance(self):
        """Get account balance"""
        try:
            response = self.api.query_private('Balance')

            if response.get('error'):
                raise Exception(f"Kraken API error: {response['error']}")

            balance = {}
            for currency, amount in response['result'].items():
                balance[currency] = float(amount)

            return balance

        except Exception as e:
            print(f"Error fetching balance: {e}")
            return None

    def get_open_orders(self):
        """Get all open orders"""
        try:
            response = self.api.query_private('OpenOrders')

            if response.get('error'):
                raise Exception(f"Kraken API error: {response['error']}")

            return response['result']['open']

        except Exception as e:
            print(f"Error fetching open orders: {e}")
            return {}

    def get_open_positions(self):
        """Get all open margin positions"""
        try:
            response = self.api.query_private('OpenPositions')

            if response.get('error'):
                if 'EGeneral:Invalid arguments' in response['error']:
                    return {}  # No open positions
                raise Exception(f"Kraken API error: {response['error']}")

            return response['result']

        except Exception as e:
            print(f"Error fetching open positions: {e}")
            return {}

    def place_order(self, order_type, side, volume, pair='XXBTZUSD',
                    price=None, leverage=None, stop_loss=None, take_profit=None):
        """
        Place an order
        order_type: 'market' or 'limit'
        side: 'buy' or 'sell'
        volume: order size
        leverage: leverage level (e.g., '3' for 3x)
        """
        try:
            params = {
                'pair': pair,
                'type': side,
                'ordertype': order_type,
                'volume': str(volume)
            }

            if price and order_type == 'limit':
                params['price'] = str(price)

            if leverage:
                params['leverage'] = str(leverage)

            # Add stop loss and take profit as separate close orders
            close_order_params = []

            if stop_loss:
                close_order_params.append(f"stop-loss:{stop_loss}")

            if take_profit:
                close_order_params.append(f"take-profit:{take_profit}")

            if close_order_params:
                params['close[ordertype]'] = 'limit'
                params['close[price]'] = ','.join(close_order_params)

            # Validate order
            params['validate'] = 'true'
            validation = self.api.query_private('AddOrder', params)

            if validation.get('error'):
                raise Exception(f"Order validation failed: {validation['error']}")

            # Place actual order
            params['validate'] = 'false'
            response = self.api.query_private('AddOrder', params)

            if response.get('error'):
                raise Exception(f"Order placement failed: {response['error']}")

            return response['result']

        except Exception as e:
            print(f"Error placing order: {e}")
            return None

    def place_market_order_with_sltp(self, side, volume, entry_price,
                                     pair='XXBTZUSD', leverage=3):
        """
        Place a market order with stop loss and take profit
        side: 'buy' or 'sell'
        volume: order size (in BTC)
        entry_price: current market price
        leverage: leverage level
        """
        try:
            # Calculate SL and TP prices
            if side == 'buy':
                take_profit_price = entry_price * (1 + Config.TAKE_PROFIT_PERCENT / 100)
                stop_loss_price = entry_price * (1 - Config.STOP_LOSS_PERCENT / 100)
            else:  # sell
                take_profit_price = entry_price * (1 - Config.TAKE_PROFIT_PERCENT / 100)
                stop_loss_price = entry_price * (1 + Config.STOP_LOSS_PERCENT / 100)

            print(f"\n📊 Order Details:")
            print(f"  Side: {side.upper()}")
            print(f"  Volume: {volume} BTC")
            print(f"  Leverage: {leverage}x")
            print(f"  Entry Price: ${entry_price:,.2f}")
            print(f"  Take Profit: ${take_profit_price:,.2f} (+{Config.TAKE_PROFIT_PERCENT}%)")
            print(f"  Stop Loss: ${stop_loss_price:,.2f} (-{Config.STOP_LOSS_PERCENT}%)")

            # Place the order
            result = self.place_order(
                order_type='market',
                side=side,
                volume=volume,
                pair=pair,
                leverage=leverage,
                take_profit=take_profit_price,
                stop_loss=stop_loss_price
            )

            return result

        except Exception as e:
            print(f"Error placing order with SL/TP: {e}")
            return None

    def cancel_order(self, txid):
        """Cancel an order by transaction ID"""
        try:
            response = self.api.query_private('CancelOrder', {'txid': txid})

            if response.get('error'):
                raise Exception(f"Order cancellation failed: {response['error']}")

            return response['result']

        except Exception as e:
            print(f"Error canceling order: {e}")
            return None

    def get_trade_history(self, start=None, end=None):
        """Get trade history"""
        try:
            params = {}
            if start:
                params['start'] = start
            if end:
                params['end'] = end

            response = self.api.query_private('TradesHistory', params)

            if response.get('error'):
                raise Exception(f"Kraken API error: {response['error']}")

            return response['result']

        except Exception as e:
            print(f"Error fetching trade history: {e}")
            return None

    def get_tradable_asset_pairs(self):
        """Get information about tradable asset pairs"""
        try:
            response = self.api.query_public('AssetPairs')

            if response.get('error'):
                raise Exception(f"Kraken API error: {response['error']}")

            return response['result']

        except Exception as e:
            print(f"Error fetching asset pairs: {e}")
            return None

    def close_position(self, pair='XXBTZUSD'):
        """Close all positions for a pair"""
        try:
            positions = self.get_open_positions()

            if not positions:
                print("No open positions to close")
                return None

            results = []
            for pos_id, pos_data in positions.items():
                # Determine opposite side to close position
                side = 'sell' if pos_data['type'] == 'buy' else 'buy'
                volume = float(pos_data['vol'])

                result = self.place_order(
                    order_type='market',
                    side=side,
                    volume=volume,
                    pair=pair
                )

                results.append(result)

            return results

        except Exception as e:
            print(f"Error closing position: {e}")
            return None
