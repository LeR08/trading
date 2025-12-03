"""
Webhook sender module for trading signals
Sends professional signals with TP, SL and confidence score
"""
import requests
import json
import logging
from datetime import datetime
from config import Config


class WebhookSender:
    """Class to send trading signals via webhook"""

    def __init__(self, webhook_url=None):
        """
        Initialize webhook sender

        Args:
            webhook_url: Webhook URL (optional, uses Config.WEBHOOK_URL by default)
        """
        self.webhook_url = webhook_url or Config.WEBHOOK_URL
        self.logger = logging.getLogger('WebhookSender')

        # Detect if it's a Discord webhook
        self.is_discord = 'discord.com/api/webhooks' in self.webhook_url.lower()

        if self.is_discord:
            from discord_webhook import DiscordWebhook
            self.discord = DiscordWebhook(self.webhook_url)
            self.logger.info("Discord webhook detected - using Discord adapter")

    def send_trading_signal(self, signal_data):
        """
        Send trading signal via webhook

        Args:
            signal_data: Dictionary with signal data
                {
                    'action': 'BUY' or 'SELL',
                    'pair': 'BTC/USD',
                    'leverage': 10,
                    'entry_price': 45000.0,
                    'take_profit': 47250.0,
                    'stop_loss': 44100.0,
                    'tp_percent': 5.0,
                    'sl_percent': 2.0,
                    'confidence_score': 85,
                    'position_size': 0.05,
                    'timeframe_analysis': {...},
                    'reason': 'Strong bullish signal across multiple timeframes',
                    'indicators': {...}
                }

        Returns:
            bool: True if successful
        """
        # Use Discord adapter if it's a Discord webhook
        if self.is_discord:
            return self.discord.send_trading_signal(signal_data)

        # Otherwise use generic webhook
        try:
            payload = self._format_signal_payload(signal_data)

            self.logger.info(f"Sending signal to webhook: {self.webhook_url}")
            self.logger.info(f"   Action: {signal_data['action']}")
            self.logger.info(f"   Confidence: {signal_data['confidence_score']}%")

            response = requests.post(
                self.webhook_url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )

            if response.status_code == 200:
                self.logger.info("Signal sent successfully!")
                return True
            else:
                self.logger.error(f"Error sending signal: {response.status_code}")
                self.logger.error(f"   Response: {response.text}")
                return False

        except requests.exceptions.Timeout:
            self.logger.error("Timeout sending webhook")
            return False
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Webhook connection error: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}", exc_info=True)
            return False

    def _format_signal_payload(self, signal_data):
        """
        Format signal payload for webhook

        Args:
            signal_data: Raw signal data

        Returns:
            dict: Formatted payload for webhook
        """
        entry = signal_data['entry_price']
        tp = signal_data['take_profit']
        sl = signal_data['stop_loss']

        tp_distance = abs(tp - entry)
        sl_distance = abs(entry - sl)
        risk_reward_ratio = tp_distance / sl_distance if sl_distance > 0 else 0

        payload = {
            'timestamp': datetime.now().isoformat(),
            'bot_version': '2.0-professional',
            'signal_type': 'MULTI_TIMEFRAME_ANALYSIS',
            'signal': {
                'action': signal_data['action'],
                'pair': signal_data['pair'],
                'leverage': signal_data['leverage'],
                'confidence_score': signal_data['confidence_score'],
                'position_size': signal_data['position_size']
            },
            'prices': {
                'entry': entry,
                'take_profit': tp,
                'stop_loss': sl,
                'current_price': entry
            },
            'targets': {
                'tp_percent': signal_data['tp_percent'],
                'sl_percent': signal_data['sl_percent'],
                'tp_distance_usd': round(tp_distance, 2),
                'sl_distance_usd': round(sl_distance, 2),
                'risk_reward_ratio': round(risk_reward_ratio, 2)
            },
            'timeframe_analysis': signal_data.get('timeframe_analysis', {}),
            'analysis': {
                'reason': signal_data['reason'],
                'indicators': signal_data.get('indicators', {}),
                'market_conditions': signal_data.get('market_conditions', {})
            },
            'recommendation': {
                'type': 'MARGIN_TRADE',
                'urgency': self._get_urgency_level(signal_data['confidence_score']),
                'risk_level': self._get_risk_level(signal_data['confidence_score'])
            }
        }

        return payload

    def _get_urgency_level(self, confidence):
        """Get urgency level based on confidence score"""
        if confidence >= 90:
            return 'IMMEDIATE'
        elif confidence >= 80:
            return 'HIGH'
        elif confidence >= 70:
            return 'MEDIUM'
        else:
            return 'LOW'

    def _get_risk_level(self, confidence):
        """Get risk level based on confidence score"""
        if confidence >= 90:
            return 'LOW'
        elif confidence >= 80:
            return 'MEDIUM'
        elif confidence >= 70:
            return 'MEDIUM_HIGH'
        else:
            return 'HIGH'

    def send_alert(self, alert_type, message, data=None):
        """
        Send general alert via webhook

        Args:
            alert_type: Alert type (ERROR, WARNING, INFO)
            message: Alert message
            data: Additional data (optional)

        Returns:
            bool: True if successful
        """
        # Use Discord adapter if it's a Discord webhook
        if self.is_discord:
            return self.discord.send_alert(alert_type, message, data)

        # Otherwise use generic webhook
        try:
            payload = {
                'timestamp': datetime.now().isoformat(),
                'alert_type': alert_type,
                'message': message,
                'data': data or {}
            }

            response = requests.post(
                self.webhook_url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=5
            )

            return response.status_code == 200

        except Exception as e:
            self.logger.error(f"Error sending alert: {e}")
            return False

    def test_webhook(self):
        """
        Test webhook connection

        Returns:
            bool: True if webhook is accessible
        """
        # Use Discord adapter if it's a Discord webhook
        if self.is_discord:
            return self.discord.test_connection()

        # Otherwise use generic webhook test
        try:
            payload = {
                'timestamp': datetime.now().isoformat(),
                'test': True,
                'message': 'Test connection from Kraken trading bot'
            }

            self.logger.info(f"Testing webhook connection: {self.webhook_url}")

            response = requests.post(
                self.webhook_url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=5
            )

            if response.status_code == 200:
                self.logger.info("Webhook accessible!")
                return True
            else:
                self.logger.warning(f"Webhook returns: {response.status_code}")
                return False

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Webhook connection error: {e}")
            return False
