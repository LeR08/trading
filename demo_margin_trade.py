#!/usr/bin/env python3
"""
Demo Margin Trading - Exemples complets d'ouverture et fermeture de positions
Montre comment trader BTC/USD avec levier 10x, TP et SL
"""
import os
import logging
from datetime import datetime
from src.api.kraken_api import KrakenAPI

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MarginTradeDemo:
    """Démonstrateur de trading margin avec exemples BUY et SELL"""

    def __init__(self, dry_run: bool = True):
        """
        Args:
            dry_run: Si True, utilise validate=True (simulation)
        """
        self.api = KrakenAPI()
        self.dry_run = dry_run
        self.pair = 'XBTUSD'
        self.leverage = 10

        logger.info("=" * 70)
        logger.info("DEMO: Trading Margin BTC/USD avec Levier 10x")
        logger.info("=" * 70)
        logger.info(f"Mode: {'SIMULATION (DRY-RUN)' if dry_run else 'REEL (ATTENTION!)'}")
        logger.info("")

    def get_current_price(self) -> float:
        """Récupère le prix actuel de BTC/USD"""
        try:
            ticker_response = self.api.get_ticker(self.pair)
            if ticker_response.get('error'):
                logger.error(f"Erreur ticker: {ticker_response['error']}")
                return None

            # Kraken peut renvoyer XXBTZUSD au lieu de XBTUSD
            result = ticker_response.get('result', {})
            pair_key = list(result.keys())[0] if result else None

            if not pair_key:
                return None

            ticker = result[pair_key]
            # 'c' = current price [price, volume]
            current_price = float(ticker['c'][0])

            logger.info(f"Prix actuel BTC/USD: ${current_price:,.2f}")
            return current_price

        except Exception as e:
            logger.error(f"Erreur récupération prix: {e}")
            return None

    def demo_buy_long(self, volume: float = 0.001):
        """
        EXEMPLE 1: Ouvrir une position LONG (BUY) avec levier 10x

        Args:
            volume: Volume en BTC (défaut 0.001 BTC)
        """
        logger.info("\n" + "=" * 70)
        logger.info("EXEMPLE 1: Position LONG (BUY) avec Levier 10x")
        logger.info("=" * 70)

        # 1. Récupérer prix actuel
        current_price = self.get_current_price()
        if not current_price:
            logger.error("Impossible d'obtenir le prix, abandon")
            return

        # 2. Calculer TP et SL
        # SL: -1% du prix (risque)
        # TP: +2% du prix (gain) -> R:R de 2:1
        sl_pct = 0.01  # 1%
        tp_pct = 0.02  # 2%

        sl_price = current_price * (1 - sl_pct)
        tp_price = current_price * (1 + tp_pct)

        logger.info(f"\n[CONFIGURATION TRADE]")
        logger.info(f"  Direction: BUY (LONG)")
        logger.info(f"  Volume: {volume} BTC")
        logger.info(f"  Prix entrée: ${current_price:,.2f}")
        logger.info(f"  Levier: {self.leverage}x")
        logger.info(f"  Take Profit: ${tp_price:,.2f} (+{tp_pct*100}%)")
        logger.info(f"  Stop Loss: ${sl_price:,.2f} (-{sl_pct*100}%)")

        # 3. Calculer la valeur de la position
        position_value = volume * current_price  # Valeur en USD
        margin_required = position_value / self.leverage

        logger.info(f"\n[MARGIN INFO]")
        logger.info(f"  Valeur position: ${position_value:,.2f}")
        logger.info(f"  Margin requis (10x): ${margin_required:,.2f}")
        logger.info(f"  Risque (si SL): ${position_value * sl_pct:,.2f}")
        logger.info(f"  Gain potentiel (si TP): ${position_value * tp_pct:,.2f}")

        # 4. Construire l'ordre
        order_params = {
            'pair': self.pair,
            'side': 'buy',
            'ordertype': 'market',
            'volume': volume,
            'leverage': self.leverage,
            'close[ordertype]': 'stop-loss-limit',
            'close[price]': str(tp_price),      # TP
            'close[price2]': str(sl_price),     # SL trigger
            'validate': self.dry_run  # True = simulation
        }

        logger.info(f"\n[PLACEMENT ORDRE]")
        logger.info(f"  Envoi ordre à Kraken...")

        # 5. Placer l'ordre
        try:
            result = self.api.add_order(**order_params)

            if result.get('error'):
                logger.error(f"[ERREUR] {result['error']}")
                return None

            order_result = result.get('result', {})

            if self.dry_run:
                logger.info(f"[OK] Ordre validé (simulation)")
                logger.info(f"  Description: {order_result.get('descr', {})}")
            else:
                txid = order_result.get('txid', [])
                logger.info(f"[OK] Ordre placé!")
                logger.info(f"  TXID: {txid}")
                logger.info(f"  Description: {order_result.get('descr', {})}")

                return txid[0] if txid else None

        except Exception as e:
            logger.error(f"[EXCEPTION] {e}")
            return None

    def demo_sell_short(self, volume: float = 0.001):
        """
        EXEMPLE 2: Ouvrir une position SHORT (SELL) avec levier 10x

        Args:
            volume: Volume en BTC (défaut 0.001 BTC)
        """
        logger.info("\n" + "=" * 70)
        logger.info("EXEMPLE 2: Position SHORT (SELL) avec Levier 10x")
        logger.info("=" * 70)

        # 1. Récupérer prix actuel
        current_price = self.get_current_price()
        if not current_price:
            logger.error("Impossible d'obtenir le prix, abandon")
            return

        # 2. Calculer TP et SL (inversés pour SHORT)
        # SL: +1% du prix (risque si prix monte)
        # TP: -2% du prix (gain si prix baisse) -> R:R de 2:1
        sl_pct = 0.01  # 1%
        tp_pct = 0.02  # 2%

        sl_price = current_price * (1 + sl_pct)  # Plus haut = perte
        tp_price = current_price * (1 - tp_pct)  # Plus bas = gain

        logger.info(f"\n[CONFIGURATION TRADE]")
        logger.info(f"  Direction: SELL (SHORT)")
        logger.info(f"  Volume: {volume} BTC")
        logger.info(f"  Prix entrée: ${current_price:,.2f}")
        logger.info(f"  Levier: {self.leverage}x")
        logger.info(f"  Take Profit: ${tp_price:,.2f} (-{tp_pct*100}%)")
        logger.info(f"  Stop Loss: ${sl_price:,.2f} (+{sl_pct*100}%)")

        # 3. Calculer la valeur de la position
        position_value = volume * current_price
        margin_required = position_value / self.leverage

        logger.info(f"\n[MARGIN INFO]")
        logger.info(f"  Valeur position: ${position_value:,.2f}")
        logger.info(f"  Margin requis (10x): ${margin_required:,.2f}")
        logger.info(f"  Risque (si SL): ${position_value * sl_pct:,.2f}")
        logger.info(f"  Gain potentiel (si TP): ${position_value * tp_pct:,.2f}")

        # 4. Construire l'ordre
        order_params = {
            'pair': self.pair,
            'side': 'sell',
            'ordertype': 'market',
            'volume': volume,
            'leverage': self.leverage,
            'close[ordertype]': 'stop-loss-limit',
            'close[price]': str(tp_price),      # TP
            'close[price2]': str(sl_price),     # SL trigger
            'validate': self.dry_run
        }

        logger.info(f"\n[PLACEMENT ORDRE]")
        logger.info(f"  Envoi ordre à Kraken...")

        # 5. Placer l'ordre
        try:
            result = self.api.add_order(**order_params)

            if result.get('error'):
                logger.error(f"[ERREUR] {result['error']}")
                return None

            order_result = result.get('result', {})

            if self.dry_run:
                logger.info(f"[OK] Ordre validé (simulation)")
                logger.info(f"  Description: {order_result.get('descr', {})}")
            else:
                txid = order_result.get('txid', [])
                logger.info(f"[OK] Ordre placé!")
                logger.info(f"  TXID: {txid}")
                logger.info(f"  Description: {order_result.get('descr', {})}")

                return txid[0] if txid else None

        except Exception as e:
            logger.error(f"[EXCEPTION] {e}")
            return None

    def show_balance(self):
        """Affiche le solde et les positions ouvertes"""
        logger.info("\n" + "=" * 70)
        logger.info("BALANCE ET POSITIONS")
        logger.info("=" * 70)

        # 1. Trade Balance
        try:
            tb_response = self.api.get_trade_balance()

            if tb_response.get('error'):
                logger.error(f"Erreur TradeBalance: {tb_response['error']}")
                return

            tb = tb_response.get('result', {})

            equity = float(tb.get('e', 0))
            margin = float(tb.get('m', 0))
            free_margin = float(tb.get('mf', 0))
            margin_level = float(tb.get('ml', 0)) if tb.get('ml') else float('inf')

            logger.info(f"\n[TRADE BALANCE]")
            logger.info(f"  Équité: ${equity:,.2f}")
            logger.info(f"  Margin utilisé: ${margin:,.2f}")
            logger.info(f"  Margin libre: ${free_margin:,.2f}")
            logger.info(f"  Margin Level: {margin_level:.1f}%")

        except Exception as e:
            logger.error(f"Erreur balance: {e}")

    def run_demos(self):
        """Exécute tous les exemples"""
        logger.info("\n[INFO] Lancement des démonstrations...")

        # Afficher balance initiale
        self.show_balance()

        # Exemple 1: Position LONG
        self.demo_buy_long(volume=0.001)

        # Exemple 2: Position SHORT
        self.demo_sell_short(volume=0.001)

        # Résumé
        logger.info("\n" + "=" * 70)
        logger.info("RESUME")
        logger.info("=" * 70)
        logger.info(f"Mode: {'SIMULATION' if self.dry_run else 'REEL'}")
        logger.info(f"\nLes ordres ont été configurés avec:")
        logger.info(f"  - Levier: {self.leverage}x")
        logger.info(f"  - TP: +2% (gain)")
        logger.info(f"  - SL: -1% (protection)")
        logger.info(f"  - R:R: 2:1 (Risk:Reward)")

        if self.dry_run:
            logger.info(f"\n[!] MODE SIMULATION: Aucun ordre réel placé")
            logger.info(f"[!] Pour trader en réel: dry_run=False")
        else:
            logger.info(f"\n[!] ORDRES REELS PLACES SUR KRAKEN")
            logger.info(f"[!] Vérifiez vos positions sur Kraken.com")


if __name__ == '__main__':
    # Mode par défaut: SIMULATION (dry_run=True)
    # Pour trader en réel: MarginTradeDemo(dry_run=False)

    demo = MarginTradeDemo(dry_run=True)
    demo.run_demos()
