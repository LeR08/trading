"""
Position Tracker - Tracks open positions and calculates real-time P&L
"""
import logging
from datetime import datetime
from config import Config


class PositionTracker:
    """Track and monitor open positions"""

    def __init__(self, kraken_client):
        """
        Initialize position tracker

        Args:
            kraken_client: KrakenClient instance
        """
        self.client = kraken_client
        self.logger = logging.getLogger('PositionTracker')
        self.paper_positions = []  # For paper trading mode

    def get_positions_status(self, current_price):
        """
        Get status of all open positions

        Args:
            current_price: Current market price

        Returns:
            dict: Position status information
        """
        # Get real positions from Kraken
        positions = self.client.get_open_positions()

        status = {
            'total_positions': len(positions),
            'positions': [],
            'total_pnl_usd': 0,
            'total_pnl_percent': 0
        }

        for pos_id, pos_data in positions.items():
            position_info = self._analyze_position(pos_id, pos_data, current_price)
            status['positions'].append(position_info)
            status['total_pnl_usd'] += position_info['pnl_usd']

        if status['total_positions'] > 0:
            avg_pnl_percent = sum(p['pnl_percent'] for p in status['positions']) / status['total_positions']
            status['total_pnl_percent'] = avg_pnl_percent

        return status

    def _analyze_position(self, pos_id, pos_data, current_price):
        """Analyze individual position"""
        try:
            side = pos_data.get('type', 'unknown')
            volume = float(pos_data.get('vol', 0))
            entry_price = float(pos_data.get('cost', 0)) / volume if volume > 0 else 0
            leverage = int(pos_data.get('leverage', 1))

            # Calculate P&L
            if side == 'buy':
                pnl_usd = (current_price - entry_price) * volume
                pnl_percent = ((current_price - entry_price) / entry_price) * 100 if entry_price > 0 else 0
            else:  # sell
                pnl_usd = (entry_price - current_price) * volume
                pnl_percent = ((entry_price - current_price) / entry_price) * 100 if entry_price > 0 else 0

            # Apply leverage effect on percentage
            pnl_percent_leveraged = pnl_percent * leverage

            position_value = volume * current_price
            initial_value = volume * entry_price

            return {
                'id': pos_id,
                'side': side.upper(),
                'volume': volume,
                'entry_price': entry_price,
                'current_price': current_price,
                'leverage': leverage,
                'pnl_usd': pnl_usd,
                'pnl_percent': pnl_percent,
                'pnl_percent_leveraged': pnl_percent_leveraged,
                'position_value': position_value,
                'initial_value': initial_value,
                'status': self._get_position_status(pnl_percent_leveraged)
            }

        except Exception as e:
            self.logger.error(f"Error analyzing position {pos_id}: {e}")
            return {
                'id': pos_id,
                'side': 'UNKNOWN',
                'volume': 0,
                'pnl_usd': 0,
                'pnl_percent': 0,
                'status': 'ERROR'
            }

    def _get_position_status(self, pnl_percent):
        """Get position status based on P&L"""
        if pnl_percent >= Config.TAKE_PROFIT_PERCENT * 0.8:
            return '🎯 NEAR TP'
        elif pnl_percent <= -Config.STOP_LOSS_PERCENT * 0.8:
            return '⚠️ NEAR SL'
        elif pnl_percent > 0:
            return '✅ PROFIT'
        elif pnl_percent < 0:
            return '🔴 LOSS'
        else:
            return '➖ NEUTRAL'

    def display_positions(self, status):
        """Display positions in console"""
        if status['total_positions'] == 0:
            self.logger.info("No open positions")
            return

        print(f"\n{'='*70}")
        print(f"📊 OPEN POSITIONS ({status['total_positions']})")
        print(f"{'='*70}")

        for i, pos in enumerate(status['positions'], 1):
            print(f"\n{i}. Position {pos['side']} - {pos['status']}")
            print(f"   Volume: {pos['volume']:.4f} BTC")
            print(f"   Entry: ${pos['entry_price']:,.2f}")
            print(f"   Current: ${pos['current_price']:,.2f}")
            print(f"   Leverage: {pos['leverage']}x")
            print(f"   P&L: ${pos['pnl_usd']:+,.2f} ({pos['pnl_percent_leveraged']:+.2f}%)")
            print(f"   Value: ${pos['position_value']:,.2f}")

        print(f"\n{'─'*70}")
        print(f"Total P&L: ${status['total_pnl_usd']:+,.2f}")
        print(f"Average P&L: {status['total_pnl_percent']:+.2f}%")
        print(f"{'='*70}\n")

    # Paper Trading Methods
    def add_paper_position(self, side, volume, entry_price, leverage, tp, sl):
        """Add a paper trading position"""
        position = {
            'id': f"PAPER_{len(self.paper_positions) + 1}",
            'side': side.upper(),
            'volume': volume,
            'entry_price': entry_price,
            'leverage': leverage,
            'take_profit': tp,
            'stop_loss': sl,
            'opened_at': datetime.now(),
            'status': 'OPEN'
        }
        self.paper_positions.append(position)
        self.logger.info(f"Paper position opened: {side.upper()} {volume} BTC @ ${entry_price:,.2f}")
        return position

    def get_paper_positions_status(self, current_price):
        """Get status of paper trading positions"""
        status = {
            'total_positions': len([p for p in self.paper_positions if p['status'] == 'OPEN']),
            'positions': [],
            'total_pnl_usd': 0,
            'total_pnl_percent': 0
        }

        for pos in self.paper_positions:
            if pos['status'] != 'OPEN':
                continue

            # Calculate P&L
            if pos['side'] == 'BUY':
                pnl_usd = (current_price - pos['entry_price']) * pos['volume']
                pnl_percent = ((current_price - pos['entry_price']) / pos['entry_price']) * 100
            else:  # SELL
                pnl_usd = (pos['entry_price'] - current_price) * pos['volume']
                pnl_percent = ((pos['entry_price'] - current_price) / pos['entry_price']) * 100

            pnl_percent_leveraged = pnl_percent * pos['leverage']

            # Check TP/SL
            if pos['side'] == 'BUY':
                if current_price >= pos['take_profit']:
                    pos['status'] = 'CLOSED_TP'
                    self.logger.info(f"Paper position {pos['id']} hit TP!")
                elif current_price <= pos['stop_loss']:
                    pos['status'] = 'CLOSED_SL'
                    self.logger.info(f"Paper position {pos['id']} hit SL!")
            else:  # SELL
                if current_price <= pos['take_profit']:
                    pos['status'] = 'CLOSED_TP'
                    self.logger.info(f"Paper position {pos['id']} hit TP!")
                elif current_price >= pos['stop_loss']:
                    pos['status'] = 'CLOSED_SL'
                    self.logger.info(f"Paper position {pos['id']} hit SL!")

            if pos['status'] == 'OPEN':
                position_info = {
                    'id': pos['id'],
                    'side': pos['side'],
                    'volume': pos['volume'],
                    'entry_price': pos['entry_price'],
                    'current_price': current_price,
                    'leverage': pos['leverage'],
                    'pnl_usd': pnl_usd,
                    'pnl_percent': pnl_percent,
                    'pnl_percent_leveraged': pnl_percent_leveraged,
                    'take_profit': pos['take_profit'],
                    'stop_loss': pos['stop_loss'],
                    'status': self._get_position_status(pnl_percent_leveraged)
                }
                status['positions'].append(position_info)
                status['total_pnl_usd'] += pnl_usd

        if status['total_positions'] > 0:
            avg_pnl = sum(p['pnl_percent_leveraged'] for p in status['positions']) / status['total_positions']
            status['total_pnl_percent'] = avg_pnl

        return status

    def close_paper_position(self, position_id, current_price, reason="MANUAL"):
        """Close a paper trading position"""
        for pos in self.paper_positions:
            if pos['id'] == position_id and pos['status'] == 'OPEN':
                pos['status'] = f'CLOSED_{reason}'
                pos['closed_at'] = datetime.now()
                pos['close_price'] = current_price

                # Calculate final P&L
                if pos['side'] == 'BUY':
                    pnl_usd = (current_price - pos['entry_price']) * pos['volume']
                else:
                    pnl_usd = (pos['entry_price'] - current_price) * pos['volume']

                self.logger.info(f"Paper position {position_id} closed: P&L = ${pnl_usd:+,.2f}")
                return True

        return False
