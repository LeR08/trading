"""
Backtest Engine Module
Moteur de backtesting avec simulation de slippage et frais de trading
"""
import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Optional
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class PositionSide(Enum):
    """Type de position"""
    LONG = "long"
    SHORT = "short"


class BacktestEngine:
    """
    Moteur de backtesting pour stratégies de trading
    Simule l'exécution d'ordres avec slippage et frais
    """

    def __init__(
        self,
        initial_capital: float,
        maker_fee: float = 0.0016,  # 0.16% Kraken maker fee
        taker_fee: float = 0.0026,  # 0.26% Kraken taker fee
        slippage_pct: float = 0.002,  # 0.2% slippage
        leverage: int = 3
    ):
        """
        Initialise le moteur de backtest

        Args:
            initial_capital: Capital initial
            maker_fee: Frais maker (ex: 0.0016 = 0.16%)
            taker_fee: Frais taker (ex: 0.0026 = 0.26%)
            slippage_pct: Slippage estimé (ex: 0.002 = 0.2%)
            leverage: Effet de levier
        """
        self.initial_capital = initial_capital
        self.maker_fee = maker_fee
        self.taker_fee = taker_fee
        self.slippage_pct = slippage_pct
        self.leverage = leverage

        # État du backtest
        self.equity = initial_capital
        self.cash = initial_capital
        self.positions: List[Dict] = []
        self.closed_positions: List[Dict] = []
        self.trades: List[Dict] = []

        # Métriques
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_fees = 0.0
        self.total_slippage = 0.0

    def run(
        self,
        strategy,
        market_data: pd.DataFrame,
        risk_per_trade: float = 0.03
    ) -> Dict:
        """
        Exécute le backtest sur les données historiques

        Args:
            strategy: Instance de stratégie (BaseStrategy)
            market_data: DataFrame OHLCV avec timestamp
            risk_per_trade: Risque par trade

        Returns:
            Dict avec résultats du backtest
        """
        logger.info(f"Démarrage backtest: {strategy.name}")
        logger.info(f"Capital initial: {self.initial_capital:.2f}")
        logger.info(f"Périodes: {len(market_data)}")

        # Reset état
        self._reset_state()

        # Itérer sur les données
        for i in range(len(market_data)):
            # Besoin d'historique minimum pour les indicateurs
            if i < 100:
                continue

            # Données jusqu'à maintenant
            current_data = market_data.iloc[:i+1]
            current_price = current_data['close'].iloc[-1]
            timestamp = current_data.index[-1] if hasattr(current_data, 'index') else i

            # Mettre à jour valeur des positions ouvertes
            self._update_positions_value(current_price)

            # Vérifier stop loss / take profit
            self._check_sl_tp(timestamp, current_price)

            # Générer signal
            signal = strategy.generate_signal(current_data)

            # Si pas de position et signal valide
            if len(self.positions) == 0 and signal['side'] in ['buy', 'sell']:
                if signal['confidence'] >= 0.6:  # Seuil de confiance
                    self._open_position(
                        timestamp,
                        signal,
                        current_price,
                        risk_per_trade
                    )

        # Fermer positions restantes
        if len(self.positions) > 0:
            final_price = market_data['close'].iloc[-1]
            final_time = market_data.index[-1] if hasattr(market_data, 'index') else len(market_data)
            for pos in self.positions[:]:  # Copie pour éviter modification pendant itération
                self._close_position(final_time, final_price, "End of backtest")

        # Calculer métriques finales
        results = self._calculate_metrics()

        logger.info(f"Backtest terminé: {self.total_trades} trades")
        logger.info(f"Équité finale: {self.equity:.2f}")
        logger.info(f"Retour: {results['total_return']:.2%}")

        return results

    def _open_position(
        self,
        timestamp,
        signal: Dict,
        current_price: float,
        risk_pct: float
    ):
        """
        Ouvre une position

        Args:
            timestamp: Timestamp de l'ouverture
            signal: Signal de trading
            current_price: Prix actuel
            risk_pct: Risque par trade
        """
        # Calculer la taille de position
        risk_amount = self.equity * risk_pct
        stop_loss_distance = abs(current_price - signal['sl']) / current_price

        if stop_loss_distance == 0:
            logger.warning("Stop loss distance nulle, skip position")
            return

        position_value = (risk_amount / stop_loss_distance) * self.leverage

        # Appliquer slippage
        if signal['side'] == 'buy':
            entry_price = current_price * (1 + self.slippage_pct)
        else:  # sell/short
            entry_price = current_price * (1 - self.slippage_pct)

        volume = position_value / entry_price

        # Calculer frais (on utilise taker fee pour market orders)
        fee = position_value * self.taker_fee
        margin_required = position_value / self.leverage

        # Vérifier si assez de capital
        if margin_required + fee > self.cash:
            logger.warning(f"Capital insuffisant: {self.cash:.2f} < {margin_required + fee:.2f}")
            return

        # Ouvrir position
        position = {
            'id': len(self.positions) + len(self.closed_positions),
            'timestamp': timestamp,
            'side': signal['side'],
            'entry_price': entry_price,
            'volume': volume,
            'position_value': position_value,
            'margin_used': margin_required,
            'leverage': self.leverage,
            'tp': signal['tp'],
            'sl': signal['sl'],
            'entry_fee': fee,
            'unrealized_pnl': 0.0,
            'current_price': entry_price
        }

        self.positions.append(position)
        self.cash -= (margin_required + fee)
        self.total_fees += fee
        self.total_slippage += abs(current_price - entry_price) * volume

        logger.info(
            f"📊 Position ouverte: {signal['side'].upper()} "
            f"{volume:.4f} @ {entry_price:.2f} "
            f"(TP: {signal['tp']:.2f}, SL: {signal['sl']:.2f})"
        )

    def _close_position(
        self,
        timestamp,
        current_price: float,
        reason: str,
        position: Optional[Dict] = None
    ):
        """
        Ferme une position

        Args:
            timestamp: Timestamp de fermeture
            current_price: Prix de fermeture
            reason: Raison de la fermeture
            position: Position à fermer (ou première si None)
        """
        if not position:
            if not self.positions:
                return
            position = self.positions[0]

        # Appliquer slippage
        if position['side'] == 'buy':
            exit_price = current_price * (1 - self.slippage_pct)
        else:  # short
            exit_price = current_price * (1 + self.slippage_pct)

        # Calculer P&L
        if position['side'] == 'buy':
            pnl_raw = (exit_price - position['entry_price']) * position['volume']
        else:  # short
            pnl_raw = (position['entry_price'] - exit_price) * position['volume']

        # Frais de sortie
        exit_fee = position['position_value'] * self.taker_fee

        # P&L net
        pnl_net = pnl_raw - position['entry_fee'] - exit_fee

        # Retourner margin
        self.cash += position['margin_used'] + pnl_net
        self.equity = self.cash + self._calculate_open_positions_value()

        # Enregistrer trade
        trade = {
            'id': position['id'],
            'entry_time': position['timestamp'],
            'exit_time': timestamp,
            'side': position['side'],
            'entry_price': position['entry_price'],
            'exit_price': exit_price,
            'volume': position['volume'],
            'pnl_gross': pnl_raw,
            'pnl_net': pnl_net,
            'fees': position['entry_fee'] + exit_fee,
            'return_pct': (pnl_net / position['margin_used']) * 100,
            'reason': reason
        }

        self.trades.append(trade)
        self.closed_positions.append(position)
        self.positions.remove(position)

        self.total_trades += 1
        if pnl_net > 0:
            self.winning_trades += 1
        else:
            self.losing_trades += 1

        self.total_fees += exit_fee
        self.total_slippage += abs(current_price - exit_price) * position['volume']

        logger.info(
            f"📈 Position fermée: {position['side'].upper()} "
            f"P&L: {pnl_net:.2f} ({trade['return_pct']:.2f}%) - {reason}"
        )

    def _update_positions_value(self, current_price: float):
        """
        Met à jour la valeur des positions ouvertes

        Args:
            current_price: Prix actuel
        """
        for pos in self.positions:
            pos['current_price'] = current_price

            # Calculer P&L non réalisé
            if pos['side'] == 'buy':
                pos['unrealized_pnl'] = (current_price - pos['entry_price']) * pos['volume']
            else:  # short
                pos['unrealized_pnl'] = (pos['entry_price'] - current_price) * pos['volume']

        # Mettre à jour equity
        self.equity = self.cash + self._calculate_open_positions_value()

    def _calculate_open_positions_value(self) -> float:
        """
        Calcule la valeur totale des positions ouvertes

        Returns:
            Valeur totale (margin + unrealized P&L)
        """
        total = 0.0
        for pos in self.positions:
            total += pos['margin_used'] + pos['unrealized_pnl']
        return total

    def _check_sl_tp(self, timestamp, current_price: float):
        """
        Vérifie les stop loss et take profit

        Args:
            timestamp: Timestamp actuel
            current_price: Prix actuel
        """
        for pos in self.positions[:]:  # Copie pour modification safe
            hit_sl = False
            hit_tp = False

            if pos['side'] == 'buy':
                if current_price <= pos['sl']:
                    hit_sl = True
                elif current_price >= pos['tp']:
                    hit_tp = True
            else:  # short
                if current_price >= pos['sl']:
                    hit_sl = True
                elif current_price <= pos['tp']:
                    hit_tp = True

            if hit_sl:
                self._close_position(timestamp, pos['sl'], "Stop Loss", pos)
            elif hit_tp:
                self._close_position(timestamp, pos['tp'], "Take Profit", pos)

    def _reset_state(self):
        """Réinitialise l'état du backtest"""
        self.equity = self.initial_capital
        self.cash = self.initial_capital
        self.positions = []
        self.closed_positions = []
        self.trades = []
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_fees = 0.0
        self.total_slippage = 0.0

    def _calculate_metrics(self) -> Dict:
        """
        Calcule les métriques de performance

        Returns:
            Dict avec métriques
        """
        if not self.trades:
            return {
                'total_return': 0.0,
                'total_return_pct': 0.0,
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0.0,
                'avg_win': 0.0,
                'avg_loss': 0.0,
                'profit_factor': 0.0,
                'max_drawdown': 0.0,
                'sharpe_ratio': 0.0,
                'total_fees': 0.0,
                'total_slippage': 0.0
            }

        # Retour total
        total_return = self.equity - self.initial_capital
        total_return_pct = (total_return / self.initial_capital)

        # Win rate
        win_rate = (self.winning_trades / self.total_trades) if self.total_trades > 0 else 0

        # Gain/perte moyens
        wins = [t['pnl_net'] for t in self.trades if t['pnl_net'] > 0]
        losses = [t['pnl_net'] for t in self.trades if t['pnl_net'] < 0]

        avg_win = np.mean(wins) if wins else 0
        avg_loss = np.mean(losses) if losses else 0

        # Profit factor
        gross_profit = sum(wins) if wins else 0
        gross_loss = abs(sum(losses)) if losses else 0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0

        # Max drawdown
        equity_curve = [self.initial_capital]
        running_equity = self.initial_capital

        for trade in self.trades:
            running_equity += trade['pnl_net']
            equity_curve.append(running_equity)

        peak = equity_curve[0]
        max_dd = 0.0

        for equity in equity_curve:
            if equity > peak:
                peak = equity
            dd = (peak - equity) / peak
            if dd > max_dd:
                max_dd = dd

        # Sharpe ratio (simplifié)
        returns = [t['return_pct'] / 100 for t in self.trades]
        if returns and len(returns) > 1:
            sharpe = (np.mean(returns) / np.std(returns)) * np.sqrt(252) if np.std(returns) > 0 else 0
        else:
            sharpe = 0.0

        return {
            'initial_capital': self.initial_capital,
            'final_equity': round(self.equity, 2),
            'total_return': round(total_return, 2),
            'total_return_pct': round(total_return_pct * 100, 2),
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': round(win_rate * 100, 2),
            'avg_win': round(avg_win, 2),
            'avg_loss': round(avg_loss, 2),
            'profit_factor': round(profit_factor, 2),
            'max_drawdown': round(max_dd * 100, 2),
            'sharpe_ratio': round(sharpe, 2),
            'total_fees': round(self.total_fees, 2),
            'total_slippage': round(self.total_slippage, 2)
        }
