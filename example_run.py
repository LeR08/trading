#!/usr/bin/env python3
"""
Example Run - Cycle complet du bot de trading
Illustre l'utilisation de tous les modules: stratégie, risk engine, executor, monitoring
"""
import os
import time
import logging
import pandas as pd
from datetime import datetime
from threading import Thread

# Import des modules
from src.api.kraken_api import KrakenAPI
from src.strategies import TrendFollowingStrategy, MeanReversionStrategy, BreakoutStrategy
from src.risk_engine import PositionSizer, CircuitBreaker, MarginChecker
from src.executor import OrderExecutor
from src.monitoring import get_metrics_instance, run_metrics_server

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class TradingBot:
    """Bot de trading principal orchestrant tous les modules"""

    def __init__(
        self,
        pair: str = 'XBTEUR',
        strategy_name: str = 'trend_following',
        leverage: int = 3,
        risk_per_trade: float = 0.03,
        dry_run: bool = True
    ):
        """
        Initialise le bot

        Args:
            pair: Paire de trading
            strategy_name: Nom de la stratégie ('trend_following', 'mean_reversion', 'breakout')
            leverage: Effet de levier
            risk_per_trade: Risque par trade
            dry_run: Mode simulation (ne place pas vraiment d'ordres)
        """
        logger.info("=" * 60)
        logger.info("[*] Initialisation du Kraken BTC Trading Bot")
        logger.info("=" * 60)

        self.pair = pair
        self.leverage = leverage
        self.risk_per_trade = risk_per_trade
        self.dry_run = dry_run

        # Initialiser API Kraken
        logger.info("[API] Connexion à l'API Kraken...")
        self.api = KrakenAPI()

        # Initialiser stratégie
        logger.info(f"[CHART] Chargement stratégie: {strategy_name}")
        self.strategy = self._init_strategy(strategy_name)

        # Initialiser risk engine
        logger.info("[SHIELD] Initialisation Risk Engine...")
        self.position_sizer = PositionSizer(
            default_risk_pct=risk_per_trade,
            max_exposure_pct=0.10,
            default_leverage=leverage
        )
        self.circuit_breaker = CircuitBreaker(
            max_drawdown_pct=0.15,
            max_daily_loss_pct=0.05,
            max_consecutive_losses=5
        )
        self.margin_checker = MarginChecker(
            min_margin_level=150.0,
            warning_margin_level=200.0
        )

        # Initialiser executor
        logger.info("[BOLT] Initialisation Order Executor...")
        self.executor = OrderExecutor(
            kraken_api=self.api,
            max_retries=5,
            base_delay=2.0
        )

        # Métriques Prometheus
        logger.info("[UP] Initialisation métriques Prometheus...")
        self.metrics = get_metrics_instance()

        logger.info("[OK] Initialisation terminée\n")

    def _init_strategy(self, name: str):
        """Initialise la stratégie sélectionnée"""
        strategies = {
            'trend_following': TrendFollowingStrategy(),
            'mean_reversion': MeanReversionStrategy(),
            'breakout': BreakoutStrategy()
        }

        if name not in strategies:
            logger.warning(f"Stratégie '{name}' inconnue, utilisation de trend_following")
            return strategies['trend_following']

        return strategies[name]

    def run_cycle(self):
        """
        Exécute un cycle complet de trading:
        1. Récupération données marché
        2. Génération signal
        3. Vérification risques
        4. Calcul taille position
        5. Placement ordre (si conditions OK)
        """
        logger.info("\n" + "=" * 60)
        logger.info(f"[CYCLE] NOUVEAU CYCLE - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 60)

        try:
            # Étape 1: Récupérer données marché
            logger.info("\n[DOWN] 1. Récupération données marché...")
            market_data = self._fetch_market_data()
            if market_data is None or market_data.empty:
                logger.error("[X] Impossible de récupérer les données marché")
                return

            current_price = market_data['close'].iloc[-1]
            logger.info(f"   Prix actuel BTC: {current_price:,.2f} EUR")

            # Étape 2: Générer signal de trading
            logger.info("\n[TARGET] 2. Génération signal de trading...")
            signal = self.strategy.generate_signal(market_data)
            logger.info(f"   Signal: {signal['side'].upper()}")
            logger.info(f"   Confiance: {signal['confidence']:.1%}")
            logger.info(f"   Raison: {signal['reason']}")
            logger.info(f"   TP: {signal['tp']:,.2f} | SL: {signal['sl']:,.2f}")

            # Mettre à jour métriques
            self.metrics.update_signal(signal)

            # Si signal neutre, on skip
            if signal['side'] == 'hold' or signal['confidence'] < 0.6:
                logger.info("[PAUSE] Pas de signal suffisant, on attend...")
                return

            # Étape 3: Vérifier TradeBalance et margin
            logger.info("\n[MONEY] 3. Vérification balance et marge...")
            trade_balance_response = self.api.get_trade_balance()

            if trade_balance_response.get('error'):
                logger.error(f"[X] Erreur TradeBalance: {trade_balance_response['error']}")
                return

            trade_balance = trade_balance_response.get('result', {})
            equity = float(trade_balance.get('e', 0))
            logger.info(f"   Équité: {equity:,.2f} EUR")

            # Vérifier marge
            margin_status = self.margin_checker.check_margin(trade_balance)
            logger.info(f"   Margin Level: {margin_status['margin_level']:.1f}%")
            logger.info(f"   Free Margin: {margin_status['free_margin']:,.2f} EUR")

            if not margin_status['sufficient']:
                logger.warning(f"[!] Marge insuffisante: {margin_status['message']}")
                return

            # Mettre à jour métriques marge
            self.metrics.update_margin(margin_status)
            self.metrics.update_equity(equity, equity)

            # Étape 4: Vérifier circuit breaker
            logger.info("\n[LOCK] 4. Vérification circuit breaker...")
            if not hasattr(self.circuit_breaker, 'initial_equity') or self.circuit_breaker.initial_equity == 0:
                self.circuit_breaker.initialize(equity)

            cb_status = self.circuit_breaker.check(equity)
            logger.info(f"   État: {cb_status['state']}")
            logger.info(f"   Drawdown: {cb_status['current_drawdown']:.2%}")

            if not cb_status['trading_allowed']:
                logger.warning(f"[RED] Circuit breaker OUVERT: {cb_status['reason']}")
                self.metrics.update_circuit_breaker(cb_status)
                return

            self.metrics.update_circuit_breaker(cb_status)

            # Étape 5: Récupérer info AssetPairs pour validation
            logger.info("\n📋 5. Récupération contraintes AssetPairs...")
            asset_pairs_response = self.api.get_asset_pairs(self.pair)

            if asset_pairs_response.get('error'):
                logger.warning(f"[!] Erreur AssetPairs: {asset_pairs_response['error']}")
                asset_pair_info = None
            else:
                asset_pair_info = asset_pairs_response.get('result', {}).get(self.pair, {})
                logger.info(f"   Order min: {asset_pair_info.get('ordermin', 'N/A')}")

            # Étape 6: Calculer taille position
            logger.info("\n[RULER] 6. Calcul taille position...")
            stop_loss_pct = abs(current_price - signal['sl']) / current_price

            position_calc = self.position_sizer.calc_size(
                equity=equity,
                price=current_price,
                risk_pct=self.risk_per_trade,
                leverage=self.leverage,
                stop_loss_pct=stop_loss_pct,
                asset_pair_info=asset_pair_info
            )

            if not position_calc['valid']:
                logger.warning(f"[!] Position invalide: {position_calc['reason']}")
                return

            logger.info(f"   Volume: {position_calc['volume']} BTC")
            logger.info(f"   Valeur position: {position_calc['position_value']:,.2f} EUR")
            logger.info(f"   Margin requis: {position_calc['margin_required']:,.2f} EUR")
            logger.info(f"   Leverage: {position_calc['leverage']}x")

            # Vérifier si on peut ouvrir la position
            can_open, reason = self.margin_checker.can_open_position(
                trade_balance,
                position_calc['margin_required']
            )

            if not can_open:
                logger.warning(f"[!] Impossible d'ouvrir position: {reason}")
                return

            # Étape 7: Placer l'ordre
            logger.info("\n[*] 7. Placement de l'ordre...")

            if self.dry_run:
                logger.info("[!] MODE DRY-RUN: L'ordre ne sera PAS réellement placé")
                logger.info(f"   Side: {signal['side'].upper()}")
                logger.info(f"   Volume: {position_calc['volume']} BTC")
                logger.info(f"   Pair: {self.pair}")
                logger.info(f"   Leverage: {self.leverage}x")
                logger.info(f"   Take Profit: {signal['tp']:,.2f}")
                logger.info(f"   Stop Loss: {signal['sl']:,.2f}")
                logger.info("[OK] Ordre simulé avec succès")

                # Mettre à jour métriques
                self.metrics.record_order('success', latency=0.5)

            else:
                # Mode PRODUCTION - placer vraiment l'ordre
                order_signal = {
                    'side': signal['side'],
                    'volume': position_calc['volume'],
                    'pair': self.pair,
                    'leverage': self.leverage,
                    'tp': signal['tp'],
                    'sl': signal['sl'],
                    'ordertype': 'market'
                }

                start_time = time.time()
                result = self.executor.place_order(order_signal)
                latency = time.time() - start_time

                if result['success']:
                    logger.info(f"[OK] Ordre placé: {result['order_id']}")
                    logger.info(f"   TxID: {result['txid']}")
                    self.metrics.record_order('success', latency)
                else:
                    logger.error(f"[X] Échec placement ordre: {result['error']}")
                    self.metrics.record_order('failed', latency)

        except Exception as e:
            logger.error(f"[X] Erreur durant le cycle: {e}", exc_info=True)
            self.metrics.record_api_error('unknown')

        finally:
            # Mettre à jour métriques système
            self.metrics.update_system()

    def _fetch_market_data(self) -> pd.DataFrame:
        """
        Récupère les données OHLC depuis Kraken

        Returns:
            DataFrame avec colonnes OHLCV
        """
        try:
            response = self.api.get_ohlc(
                pair=self.pair,
                interval=60  # 1 heure
            )

            if response.get('error'):
                logger.error(f"Erreur OHLC: {response['error']}")
                return None

            # Kraken peut retourner une clé différente de celle demandée
            # Ex: XBTEUR -> XXBTZEUR
            result_keys = list(response['result'].keys())
            # Filtrer 'last' qui est un timestamp
            pair_keys = [k for k in result_keys if k != 'last']

            if not pair_keys:
                logger.error("Aucune donnée OHLC retournée")
                return None

            # Prendre la première paire disponible
            actual_pair = pair_keys[0]
            logger.debug(f"Paire demandée: {self.pair}, paire reçue: {actual_pair}")

            ohlc_data = response['result'][actual_pair]

            # Convertir en DataFrame
            df = pd.DataFrame(ohlc_data, columns=[
                'time', 'open', 'high', 'low', 'close', 'vwap', 'volume', 'count'
            ])

            # Convertir types
            df['time'] = pd.to_datetime(df['time'], unit='s')
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)

            return df

        except Exception as e:
            logger.error(f"Exception lors fetch market data: {e}")
            return None

    def run(self, interval_seconds: int = 300):
        """
        Lance le bot en mode continu

        Args:
            interval_seconds: Intervalle entre cycles (en secondes)
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"[BOT] DÉMARRAGE DU BOT")
        logger.info(f"   Paire: {self.pair}")
        logger.info(f"   Stratégie: {self.strategy.name}")
        logger.info(f"   Leverage: {self.leverage}x")
        logger.info(f"   Risque/trade: {self.risk_per_trade:.1%}")
        logger.info(f"   Mode: {'DRY-RUN' if self.dry_run else 'PRODUCTION'}")
        logger.info(f"   Intervalle: {interval_seconds}s")
        logger.info(f"{'='*60}\n")

        cycle_count = 0

        try:
            while True:
                cycle_count += 1
                logger.info(f"\n[PIN] Cycle #{cycle_count}")

                self.run_cycle()

                logger.info(f"\n[TIME] Pause de {interval_seconds}s avant prochain cycle...")
                time.sleep(interval_seconds)

        except KeyboardInterrupt:
            logger.info("\n\n⏹️ Arrêt du bot par l'utilisateur")
        except Exception as e:
            logger.error(f"\n\n[BANG] Erreur fatale: {e}", exc_info=True)
        finally:
            logger.info("\n[WAVE] Bot arrêté")


def main():
    """Point d'entrée principal"""
    # Lire config depuis env vars
    pair = os.getenv('PAIR', 'XBTEUR')
    leverage = int(os.getenv('LEVERAGE', '3'))
    risk_per_trade = float(os.getenv('RISK_PER_TRADE', '0.03'))
    strategy_name = os.getenv('STRATEGY', 'trend_following')
    dry_run = os.getenv('DRY_RUN', 'true').lower() == 'true'
    interval = int(os.getenv('INTERVAL_SECONDS', '300'))

    # Démarrer serveur métriques dans un thread séparé
    logger.info("[WEB] Démarrage serveur métriques...")
    metrics_thread = Thread(
        target=run_metrics_server,
        args=('0.0.0.0', 9090),
        daemon=True
    )
    metrics_thread.start()

    # Petit délai pour que le serveur démarre
    time.sleep(2)
    logger.info("[OK] Serveur métriques démarré sur http://0.0.0.0:9090/metrics\n")

    # Créer et lancer bot
    bot = TradingBot(
        pair=pair,
        strategy_name=strategy_name,
        leverage=leverage,
        risk_per_trade=risk_per_trade,
        dry_run=dry_run
    )

    bot.run(interval_seconds=interval)


if __name__ == '__main__':
    main()
