"""
Multi-timeframe analyzer for professional trading
Analyzes all available Kraken API timeframes
"""
import pandas as pd
import logging
from datetime import datetime
from indicators import TechnicalIndicators
from config import Config


class MultiTimeframeAnalyzer:
    """
    Professional multi-timeframe analyzer

    Available Kraken timeframes (in minutes):
    - 1: 1 minute
    - 5: 5 minutes
    - 15: 15 minutes
    - 30: 30 minutes
    - 60: 1 hour
    - 240: 4 hours
    - 1440: 1 day
    - 10080: 1 week
    - 21600: 15 days
    """

    ALL_TIMEFRAMES = [1, 5, 15, 30, 60, 240, 1440, 10080, 21600]

    TIMEFRAME_NAMES = {
        1: '1m',
        5: '5m',
        15: '15m',
        30: '30m',
        60: '1h',
        240: '4h',
        1440: '1D',
        10080: '1W',
        21600: '15D'
    }

    def __init__(self, kraken_client):
        """
        Initialize multi-timeframe analyzer

        Args:
            kraken_client: KrakenClient instance
        """
        self.client = kraken_client
        self.logger = logging.getLogger('MultiTimeframeAnalyzer')

        self.timeframes = Config.TIMEFRAMES if hasattr(Config, 'TIMEFRAMES') else self.ALL_TIMEFRAMES
        self.weights = Config.TIMEFRAME_WEIGHTS if hasattr(Config, 'TIMEFRAME_WEIGHTS') else self._default_weights()

        self.logger.info(f"Multi-Timeframe Analyzer initialized")
        self.logger.info(f"   Timeframes: {[self.TIMEFRAME_NAMES[tf] for tf in self.timeframes]}")

    def _default_weights(self):
        """Default weights for each timeframe"""
        return {
            1: 1,      # 1m: low weight (noise)
            5: 2,      # 5m: low weight
            15: 3,     # 15m: medium weight
            30: 4,     # 30m: medium weight
            60: 5,     # 1h: high weight (good balance)
            240: 6,    # 4h: high weight (medium term trend)
            1440: 7,   # 1D: maximum weight (long term trend)
            10080: 5,  # 1W: high weight
            21600: 3   # 15D: medium weight
        }

    def analyze_all_timeframes(self, pair='XXBTZUSD'):
        """
        Analyze all configured timeframes

        Args:
            pair: Trading pair

        Returns:
            dict: Multi-timeframe analysis results with confidence score
        """
        self.logger.info(f"\n{'='*70}")
        self.logger.info("MULTI-TIMEFRAME ANALYSIS IN PROGRESS")
        self.logger.info(f"{'='*70}")

        results = {
            'timestamp': datetime.now(),
            'pair': pair,
            'timeframe_signals': {},
            'overall_signal': 'HOLD',
            'confidence_score': 0,
            'bullish_weight': 0,
            'bearish_weight': 0,
            'neutral_weight': 0,
            'total_weight': 0,
            'convergence': False,
            'convergence_ratio': 0,
            'reason': '',
            'best_timeframes': [],
            'indicators_summary': {}
        }

        total_weight = 0
        bullish_weight = 0
        bearish_weight = 0
        neutral_weight = 0

        for timeframe in self.timeframes:
            tf_name = self.TIMEFRAME_NAMES[timeframe]
            weight = self.weights.get(timeframe, 1)

            self.logger.info(f"\nAnalyzing {tf_name} (weight: {weight})...")

            try:
                df = self.client.get_ohlc_data(pair=pair, interval=timeframe)

                if df is None or len(df) < 100:
                    self.logger.warning(f"Insufficient data for {tf_name}")
                    continue

                indicators = TechnicalIndicators(df.tail(100))
                df_with_indicators = indicators.calculate_all()
                signal_data = indicators.get_trading_signals()

                if not signal_data:
                    self.logger.warning(f"Cannot get signals for {tf_name}")
                    continue

                signal = signal_data['signal']
                strength = signal_data['strength']

                self.logger.info(f"   Signal: {signal.upper()}")
                self.logger.info(f"   Strength: {strength:.1f}%")

                results['timeframe_signals'][tf_name] = {
                    'timeframe': timeframe,
                    'signal': signal,
                    'strength': strength,
                    'weight': weight,
                    'weighted_strength': strength * weight,
                    'indicators': signal_data['indicators'],
                    'reason': signal_data['reason']
                }

                total_weight += weight

                if signal == 'buy':
                    bullish_weight += weight * (strength / 100)
                elif signal == 'sell':
                    bearish_weight += weight * (strength / 100)
                else:
                    neutral_weight += weight

            except Exception as e:
                self.logger.error(f"Error analyzing {tf_name}: {e}")
                continue

        if total_weight > 0:
            results['total_weight'] = total_weight
            results['bullish_weight'] = bullish_weight
            results['bearish_weight'] = bearish_weight
            results['neutral_weight'] = neutral_weight

            if bullish_weight > bearish_weight and bullish_weight > neutral_weight:
                results['overall_signal'] = 'BUY'
                results['confidence_score'] = min(100, int((bullish_weight / total_weight) * 150))
            elif bearish_weight > bullish_weight and bearish_weight > neutral_weight:
                results['overall_signal'] = 'SELL'
                results['confidence_score'] = min(100, int((bearish_weight / total_weight) * 150))
            else:
                results['overall_signal'] = 'HOLD'
                results['confidence_score'] = 0

            dominant_weight = max(bullish_weight, bearish_weight)
            convergence_ratio = (dominant_weight / total_weight) * 100
            results['convergence'] = convergence_ratio > 75
            results['convergence_ratio'] = convergence_ratio

            results['best_timeframes'] = self._get_best_timeframes(
                results['timeframe_signals'],
                results['overall_signal']
            )

            results['reason'] = self._generate_reason(results)

        self.logger.info(f"\n{'='*70}")
        self.logger.info("MULTI-TIMEFRAME ANALYSIS RESULTS")
        self.logger.info(f"{'='*70}")
        self.logger.info(f"Overall Signal: {results['overall_signal']}")
        self.logger.info(f"Confidence Score: {results['confidence_score']}%")
        self.logger.info(f"Convergence: {'YES' if results['convergence'] else 'NO'} ({convergence_ratio:.1f}%)")
        self.logger.info(f"Reason: {results['reason']}")
        self.logger.info(f"{'='*70}\n")

        return results

    def _get_best_timeframes(self, timeframe_signals, overall_signal):
        """Identify the best performing timeframes"""
        matching_timeframes = []

        for tf_name, tf_data in timeframe_signals.items():
            if tf_data['signal'] == overall_signal.lower():
                matching_timeframes.append({
                    'timeframe': tf_name,
                    'strength': tf_data['strength'],
                    'weight': tf_data['weight'],
                    'weighted_score': tf_data['strength'] * tf_data['weight']
                })

        matching_timeframes.sort(key=lambda x: x['weighted_score'], reverse=True)

        return matching_timeframes[:5]

    def _generate_reason(self, results):
        """Generate detailed reason for signal"""
        signal = results['overall_signal']
        confidence = results['confidence_score']
        convergence = results['convergence']
        best_tfs = results['best_timeframes']
        convergence_ratio = results['convergence_ratio']

        if signal == 'HOLD':
            return "Mixed signals across timeframes. No clear direction."

        direction = "bullish" if signal == 'BUY' else "bearish"
        convergence_text = "strong convergence" if convergence else "moderate convergence"

        tf_list = ", ".join([tf['timeframe'] for tf in best_tfs[:3]])

        reason = f"{direction.capitalize()} trend with {convergence_text} ({convergence_ratio:.0f}%). "
        reason += f"Strong signals on: {tf_list}. "
        reason += f"Confidence score: {confidence}%."

        return reason

    def get_comprehensive_analysis(self, pair='XXBTZUSD'):
        """Get comprehensive analysis with all details"""
        mtf_results = self.analyze_all_timeframes(pair)

        ticker = self.client.get_ticker(pair)
        current_price = ticker['last'] if ticker else 0

        if mtf_results['overall_signal'] == 'BUY':
            take_profit = current_price * (1 + Config.TAKE_PROFIT_PERCENT / 100)
            stop_loss = current_price * (1 - Config.STOP_LOSS_PERCENT / 100)
        elif mtf_results['overall_signal'] == 'SELL':
            take_profit = current_price * (1 - Config.TAKE_PROFIT_PERCENT / 100)
            stop_loss = current_price * (1 + Config.STOP_LOSS_PERCENT / 100)
        else:
            take_profit = current_price
            stop_loss = current_price

        comprehensive_analysis = {
            'timestamp': datetime.now().isoformat(),
            'pair': pair,
            'current_price': current_price,
            'action': mtf_results['overall_signal'],
            'confidence_score': mtf_results['confidence_score'],
            'leverage': Config.LEVERAGE,
            'entry_price': current_price,
            'take_profit': take_profit,
            'stop_loss': stop_loss,
            'tp_percent': Config.TAKE_PROFIT_PERCENT,
            'sl_percent': Config.STOP_LOSS_PERCENT,
            'timeframe_analysis': {
                'overall_signal': mtf_results['overall_signal'],
                'convergence': mtf_results['convergence'],
                'convergence_ratio': mtf_results['convergence_ratio'],
                'bullish_weight': mtf_results['bullish_weight'],
                'bearish_weight': mtf_results['bearish_weight'],
                'total_weight': mtf_results['total_weight'],
                'best_timeframes': mtf_results['best_timeframes'],
                'all_signals': mtf_results['timeframe_signals']
            },
            'reason': mtf_results['reason'],
            'should_trade': self._should_trade(mtf_results),
            'indicators': self._get_best_indicators(mtf_results)
        }

        return comprehensive_analysis

    def _should_trade(self, mtf_results):
        """Determine if we should trade based on analysis"""
        if mtf_results['overall_signal'] == 'HOLD':
            return False

        if mtf_results['confidence_score'] < Config.MIN_CONFIDENCE_SCORE:
            return False

        if mtf_results['confidence_score'] >= 85:
            return True

        return mtf_results['convergence']

    def _get_best_indicators(self, mtf_results):
        """Extract indicators from best performing timeframe"""
        best_timeframes = mtf_results['best_timeframes']

        if not best_timeframes:
            return {}

        best_tf_name = best_timeframes[0]['timeframe']
        best_tf_data = mtf_results['timeframe_signals'].get(best_tf_name, {})

        return best_tf_data.get('indicators', {})

    def display_analysis_summary(self, analysis):
        """Display detailed analysis summary"""
        print(f"\n{'='*70}")
        print("COMPLETE MULTI-TIMEFRAME ANALYSIS")
        print(f"{'='*70}")

        print(f"\nCurrent Price: ${analysis['current_price']:,.2f}")
        print(f"Recommended Action: {analysis['action']}")
        print(f"Confidence Score: {analysis['confidence_score']}%")
        print(f"Leverage: {analysis['leverage']}x")

        if analysis['action'] != 'HOLD':
            print(f"\nTargets:")
            print(f"   Entry: ${analysis['entry_price']:,.2f}")
            print(f"   Take Profit: ${analysis['take_profit']:,.2f} (+{analysis['tp_percent']}%)")
            print(f"   Stop Loss: ${analysis['stop_loss']:,.2f} (-{analysis['sl_percent']}%)")

        mtf = analysis['timeframe_analysis']
        print(f"\nMulti-Timeframe Analysis:")
        print(f"   Convergence: {'YES' if mtf['convergence'] else 'NO'} ({mtf['convergence_ratio']:.1f}%)")
        print(f"   Bullish Weight: {mtf['bullish_weight']:.2f}")
        print(f"   Bearish Weight: {mtf['bearish_weight']:.2f}")

        print(f"\nTop 3 Timeframes:")
        for i, tf in enumerate(mtf['best_timeframes'][:3], 1):
            print(f"   {i}. {tf['timeframe']}: {tf['strength']:.1f}% (weight: {tf['weight']})")

        print(f"\nReason:")
        print(f"   {analysis['reason']}")

        print(f"\nShould Trade: {'YES' if analysis['should_trade'] else 'NO'}")

        print(f"{'='*70}\n")
