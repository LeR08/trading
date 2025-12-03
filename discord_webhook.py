"""
Discord Webhook Adapter for Trading Signals
Formats trading signals for Discord with rich embeds
"""
import requests
import logging
from datetime import datetime


class DiscordWebhook:
    """Discord webhook adapter for trading signals"""

    def __init__(self, webhook_url):
        """Initialize Discord webhook"""
        self.webhook_url = webhook_url
        self.logger = logging.getLogger('DiscordWebhook')

    def send_trading_signal(self, signal_data):
        """
        Send trading signal to Discord with rich embed

        Args:
            signal_data: Trading signal data

        Returns:
            bool: True if successful
        """
        try:
            embed = self._create_signal_embed(signal_data)
            
            payload = {
                "username": "Kraken Trading Bot",
                "avatar_url": "https://i.imgur.com/4M34hi2.png",
                "embeds": [embed]
            }

            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=10
            )

            if response.status_code == 204:
                self.logger.info("Signal sent to Discord successfully!")
                return True
            else:
                self.logger.error(f"Discord returned: {response.status_code}")
                self.logger.error(f"Response: {response.text}")
                return False

        except Exception as e:
            self.logger.error(f"Error sending to Discord: {e}")
            return False

    def _create_signal_embed(self, signal_data):
        """Create Discord embed for trading signal"""
        action = signal_data['action']
        confidence = signal_data['confidence_score']
        
        # Color based on action (green for BUY, red for SELL)
        color = 0x00ff00 if action == 'BUY' else 0xff0000
        
        # Emoji based on action
        emoji = "📈" if action == 'BUY' else "📉"
        
        # Urgency emoji
        if confidence >= 90:
            urgency_emoji = "🔥🔥🔥"
        elif confidence >= 80:
            urgency_emoji = "🔥🔥"
        elif confidence >= 70:
            urgency_emoji = "🔥"
        else:
            urgency_emoji = "⚠️"

        embed = {
            "title": f"{emoji} {action} SIGNAL - {signal_data['pair']} {urgency_emoji}",
            "color": color,
            "timestamp": datetime.now().isoformat(),
            "fields": [
                {
                    "name": "💰 Entry Price",
                    "value": f"${signal_data['entry_price']:,.2f}",
                    "inline": True
                },
                {
                    "name": "📊 Confidence",
                    "value": f"**{confidence}%**",
                    "inline": True
                },
                {
                    "name": "⚡ Leverage",
                    "value": f"{signal_data['leverage']}x",
                    "inline": True
                },
                {
                    "name": "🎯 Take Profit",
                    "value": f"${signal_data['take_profit']:,.2f}\n(+{signal_data['tp_percent']}%)",
                    "inline": True
                },
                {
                    "name": "🛡️ Stop Loss",
                    "value": f"${signal_data['stop_loss']:,.2f}\n(-{signal_data['sl_percent']}%)",
                    "inline": True
                },
                {
                    "name": "📦 Position Size",
                    "value": f"{signal_data['position_size']} BTC",
                    "inline": True
                }
            ],
            "footer": {
                "text": "Professional Multi-Timeframe Analysis"
            }
        }

        # Add timeframe analysis
        mtf = signal_data.get('timeframe_analysis', {})
        if mtf:
            convergence_text = "✅ YES" if mtf.get('convergence') else "❌ NO"
            convergence_pct = mtf.get('convergence_ratio', 0)
            
            embed['fields'].append({
                "name": "📈 Multi-Timeframe Analysis",
                "value": f"Convergence: {convergence_text} ({convergence_pct:.1f}%)\n"
                        f"Bullish: {mtf.get('bullish_weight', 0):.2f} | "
                        f"Bearish: {mtf.get('bearish_weight', 0):.2f}",
                "inline": False
            })

            # Add best timeframes
            best_tfs = mtf.get('best_timeframes', [])[:3]
            if best_tfs:
                tf_text = "\n".join([
                    f"• {tf['timeframe']}: {tf['strength']:.1f}%"
                    for tf in best_tfs
                ])
                embed['fields'].append({
                    "name": "🏆 Top Timeframes",
                    "value": tf_text,
                    "inline": False
                })

        # Add reason
        embed['fields'].append({
            "name": "💡 Analysis",
            "value": signal_data['reason'],
            "inline": False
        })

        return embed

    def send_alert(self, alert_type, message, data=None):
        """Send alert to Discord"""
        try:
            # Color based on alert type
            colors = {
                'ERROR': 0xff0000,
                'WARNING': 0xffa500,
                'INFO': 0x00bfff,
                'SUCCESS': 0x00ff00
            }
            
            color = colors.get(alert_type, 0x808080)
            
            embed = {
                "title": f"{alert_type}: {message}",
                "color": color,
                "timestamp": datetime.now().isoformat()
            }

            if data:
                embed["description"] = f"```json\n{data}\n```"

            payload = {
                "username": "Kraken Trading Bot",
                "embeds": [embed]
            }

            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=5
            )

            return response.status_code == 204

        except Exception as e:
            self.logger.error(f"Error sending alert: {e}")
            return False

    def test_connection(self):
        """Test Discord webhook connection"""
        try:
            payload = {
                "username": "Kraken Trading Bot",
                "content": "✅ Test connection successful! Bot is ready to send trading signals."
            }

            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=5
            )

            if response.status_code == 204:
                self.logger.info("Discord webhook accessible!")
                return True
            else:
                self.logger.warning(f"Discord returned: {response.status_code}")
                return False

        except Exception as e:
            self.logger.error(f"Discord connection error: {e}")
            return False
