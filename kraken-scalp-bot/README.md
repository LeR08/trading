# Kraken Scalp Bot — BTC/USD Margin Trading Bot (×3 Leverage)

Professional scalping bot for Kraken exchange specializing in BTC/USD with 3x leverage, using 12 technical indicators and confidence-based signal validation.

## Features

- **Multi-timeframe Analysis**: 3-minute and 15-minute candles
- **12 Technical Indicators**: EMA(8, 21), SMA(50), RSI(14), MACD, ATR(14), Bollinger Bands, Stochastic, ADX(14), CCI(20), OBV, VWAP
- **Confidence-Based Signals**: Only trades when confidence ≥ 66%
- **Advanced Risk Management**: Position sizing, margin checks, circuit breakers, exposure limits
- **3x Leverage Support**: Built-in margin calculations and safety checks
- **Multiple Execution Modes**: Paper trading, validation, and live execution
- **Prometheus Metrics**: Real-time monitoring and alerting
- **Comprehensive Backtesting**: Historical strategy validation with slippage and fees

## Architecture

```
kraken-scalp-bot/
├── src/
│   ├── collector/          # OHLCV data collection
│   │   ├── kraken_client.py
│   │   └── ohlcv_collector.py
│   ├── indicators/         # Technical indicators (12)
│   │   └── technical_indicators.py
│   ├── signal_engine/      # Signal generation & confidence
│   │   └── signal_generator.py
│   ├── risk_engine/        # Risk management & position sizing
│   │   └── risk_manager.py
│   ├── executor/           # Order execution
│   │   └── order_executor.py
│   ├── backtest/           # Backtesting engine
│   │   └── backtest_engine.py
│   ├── monitoring/         # Metrics & alerting
│   │   └── metrics.py
│   ├── utils/              # Configuration & utilities
│   │   └── config.py
│   └── bot.py              # Main orchestrator
├── config/
│   └── config.yaml         # Bot configuration
├── tests/
│   └── unit/               # Unit tests
├── docker/
│   └── Dockerfile
├── k8s/
│   └── deployment.yaml     # Kubernetes manifests
└── example_run.py          # Example usage
```

## Installation

### Requirements

- Python 3.11+
- Kraken API credentials with trading permissions (NO withdrawal permissions)

### Setup

1. **Clone repository**
```bash
git clone <repository>
cd kraken-scalp-bot
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Configure environment**
```bash
# Copy .env template
cp .env.example .env

# Edit .env and add your Kraken API keys
# IMPORTANT: Only add KRK_KEY and KRK_SECRET here!
nano .env
```

4. **Configure bot settings**
```bash
# Edit config.yaml for all other settings
nano config/config.yaml
```

## Configuration

### Environment Variables (.env)

**CRITICAL**: The `.env` file should ONLY contain API credentials:

```env
KRK_KEY=your_kraken_api_key_here
KRK_SECRET=your_kraken_api_secret_here
```

### Bot Configuration (config/config.yaml)

All other settings (risk parameters, indicator weights, thresholds) go in `config.yaml`:

```yaml
trading:
  pair: "XBTUSD"
  leverage: 3
  timeframes: [3, 15]
  refresh_interval: 40  # seconds
  mode: "paper"  # paper, validate, or live

signal:
  confidence_threshold: 0.66  # 66%
  weights:
    # Indicator weights (must sum to 1.0)
    ema_8: 0.08
    ema_21: 0.10
    # ... see config.yaml for all 12

risk:
  risk_per_trade: 0.01  # 1% per trade
  max_total_exposure: 0.05  # 5% max
  leverage: 3
  sl_atr_multiplier: 1.0
  tp_reward_ratio: 0.7
```

## Usage

### Paper Trading Mode (Recommended First)

```bash
python -m src.bot
```

Or using the example script:

```bash
python example_run.py
# Select option 1: Run in paper mode
```

### Validation Mode (Dry-run with Kraken)

1. Set mode in `config.yaml`:
```yaml
trading:
  mode: "validate"
```

2. Run:
```bash
python -m src.bot
```

### Live Trading Mode

⚠️ **WARNING**: Only use after extensive testing!

1. Set mode in `config.yaml`:
```yaml
trading:
  mode: "live"
```

2. Run:
```bash
python -m src.bot
```

### Backtesting

```bash
python example_run.py
# Select option 2: Run backtest example
```

### Calculate Indicators

```bash
python example_run.py
# Select option 3: Calculate indicators on live data
```

## Monitoring

### Prometheus Metrics

The bot exposes metrics on port 8000 (configurable):

```bash
curl http://localhost:8000/metrics
```

**Available metrics**:
- `bot_trades_total`: Total trades by direction and outcome
- `bot_pnl_total`: Realized/unrealized P&L
- `bot_equity`: Current equity
- `bot_margin_level`: Margin utilization
- `bot_signal_confidence`: Signal confidence by timeframe
- `bot_open_positions`: Number of open positions
- `bot_api_requests_total`: API request counters
- `bot_errors_total`: Error counters
- `bot_circuit_breaker_active`: Circuit breaker status

### Logs

Logs are output to stdout with configurable level:

```yaml
monitoring:
  log_level: "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
```

## Docker Deployment

### Build Image

```bash
docker build -t kraken-scalp-bot:latest .
```

### Run Container

```bash
docker run -d \
  --name scalp-bot \
  -p 8000:8000 \
  -v $(pwd)/.env:/app/.env:ro \
  -v $(pwd)/config:/app/config:ro \
  kraken-scalp-bot:latest
```

## Kubernetes Deployment

### Prerequisites

- Kubernetes cluster
- kubectl configured
- Prometheus Operator (optional, for ServiceMonitor)

### Deploy

1. **Update secrets** in `k8s/deployment.yaml`:
```yaml
stringData:
  KRK_KEY: "your_actual_api_key"
  KRK_SECRET: "your_actual_api_secret"
```

2. **Apply manifests**:
```bash
kubectl apply -f k8s/deployment.yaml
```

3. **Check status**:
```bash
kubectl -n trading-bot get pods
kubectl -n trading-bot logs -f deployment/kraken-scalp-bot
```

4. **Access metrics**:
```bash
kubectl -n trading-bot port-forward svc/scalp-bot-metrics 8000:8000
curl http://localhost:8000/metrics
```

## Testing

### Run Unit Tests

```bash
python -m pytest tests/unit/ -v
```

### Individual Test Modules

```bash
# Test indicators
python -m pytest tests/unit/test_indicators.py -v

# Test risk manager
python -m pytest tests/unit/test_risk_manager.py -v

# Test signal generator
python -m pytest tests/unit/test_signal_generator.py -v
```

## Pre-Deployment Checklist

### 1. Kraken API Setup

- [ ] Create Kraken API key with **trading permissions only** (no withdrawal)
- [ ] Verify API key has margin trading enabled for BTC/USD
- [ ] Test API connection in validation mode
- [ ] Check `AssetPairs` endpoint for BTC/USD specifications:
  ```python
  async with KrakenClient(api_key, api_secret) as client:
      pairs = await client.get_asset_pairs("XBTUSD")
      print(pairs)  # Check ordermin, leverage_buy, pair_decimals
  ```

### 2. Configuration Validation

- [ ] `.env` file contains ONLY `KRK_KEY` and `KRK_SECRET`
- [ ] All other configs are in `config/config.yaml`
- [ ] Indicator weights sum to 1.0
- [ ] Confidence threshold is reasonable (66-75%)
- [ ] Risk parameters are conservative:
  - [ ] `risk_per_trade: 0.01` (1% max)
  - [ ] `max_total_exposure: 0.05` (5% max)
  - [ ] `max_concurrent_trades: 3` or less
- [ ] Leverage is set to 3
- [ ] Timeframes are [3, 15]

### 3. Paper Trading Validation

- [ ] Run paper trading for minimum 2-4 weeks
- [ ] Verify signal generation logic
- [ ] Check indicator calculations match expectations
- [ ] Monitor confidence scores
- [ ] Validate SL/TP placement
- [ ] Review position sizing calculations

### 4. Backtesting

- [ ] Run backtest on minimum 1 year of data
- [ ] Test different market conditions (bull, bear, sideways)
- [ ] Analyze:
  - [ ] Win rate > 40%
  - [ ] Profit factor > 1.5
  - [ ] Max drawdown < 15%
  - [ ] Sharpe ratio > 0.5
- [ ] Sensitivity analysis on slippage (0.1% - 0.5%)
- [ ] Fee impact analysis

### 5. Risk Management Verification

- [ ] Test `TradeBalance` API call works correctly
- [ ] Verify margin calculations for 3x leverage
- [ ] Test circuit breaker triggers:
  - [ ] Daily drawdown > 3%
  - [ ] Total drawdown > 10%
- [ ] Verify position sizing respects equity limits
- [ ] Test concurrent trade limits
- [ ] Verify exposure limits work

### 6. Execution Testing

- [ ] Test order placement in validation mode
- [ ] Verify price precision (8 decimals for BTC)
- [ ] Test volume precision
- [ ] Verify SL/TP orders are placed correctly
- [ ] Test retry logic with mock failures
- [ ] Verify idempotency (clientOrderID)
- [ ] Test rate limit handling

### 7. Monitoring Setup

- [ ] Prometheus metrics endpoint accessible
- [ ] Grafana dashboard configured (optional)
- [ ] Alert rules configured:
  - [ ] Circuit breaker activation
  - [ ] API errors > threshold
  - [ ] Margin level < threshold
  - [ ] Order rejections
- [ ] Slack/email notifications configured (optional)

### 8. Security

- [ ] `.env` file is in `.gitignore`
- [ ] API secrets not logged
- [ ] Kubernetes secrets properly encrypted
- [ ] API key rotation policy established
- [ ] Access control (RBAC) configured
- [ ] No withdrawal permissions on API key

### 9. Operational Readiness

- [ ] Runbook for common issues documented
- [ ] Procedure for emergency shutdown
- [ ] Procedure for circuit breaker reset
- [ ] Backup of configuration
- [ ] Monitoring dashboards accessible
- [ ] On-call rotation established (if applicable)

### 10. Final Checks

- [ ] Verify trading pair: BTC/USD
- [ ] Verify leverage: 3x
- [ ] Verify mode: Start with "paper", then "validate", finally "live"
- [ ] Sufficient equity in Kraken account
- [ ] Test emergency stop (Ctrl+C / SIGTERM)
- [ ] Document initial equity baseline

## Signal Generation Logic

### Confidence Calculation

1. Each indicator provides normalized signal: `-1` (bearish), `0` (neutral), `+1` (bullish)
2. Each indicator has a configurable weight (sum = 1.0)
3. Raw score = Σ(weight × signal) ∈ [-1, +1]
4. Confidence = |raw_score| × 100%
5. Trade only if confidence ≥ 66%

### Multi-Timeframe Confirmation

- Primary timeframe (3m) generates initial signal
- Higher timeframe (15m) must confirm or be neutral
- If conflict between timeframes → NEUTRAL (no trade)

## Risk Management

### Position Sizing

```
Risk Amount = Equity × risk_per_trade (1%)
Position Size = Risk Amount / |Entry Price - Stop Loss|
Margin Required = (Position Size × Entry Price) / Leverage
```

### Stop Loss Calculation

```
SL Distance = ATR(14) × atr_multiplier (1.0)
Long SL = Entry Price - SL Distance
Short SL = Entry Price + SL Distance
```

### Take Profit Calculation

```
TP Distance = SL Distance × tp_reward_ratio (0.7)
Long TP = Entry Price + TP Distance
Short TP = Entry Price - TP Distance
```

### Circuit Breakers

- **Daily drawdown > 3%**: Stop trading for the day
- **Total drawdown > 10%**: Stop trading until manual reset
- **Insufficient margin**: Reject new positions
- **Max concurrent trades**: No new positions if limit reached

## Troubleshooting

### Common Issues

**1. "Insufficient margin" error**

Check your available margin:
```python
trade_balance = await client.get_trade_balance()
print(f"Free margin: {trade_balance['mf']}")
```

**2. API rate limiting**

Bot has built-in retry with exponential backoff. If persistent:
- Increase `refresh_interval` in config
- Reduce concurrent operations

**3. Order precision errors**

Verify asset pair specifications:
```python
pairs = await client.get_asset_pairs("XBTUSD")
# Check pair_decimals (price) and lot_decimals (volume)
```

**4. Circuit breaker activated**

Check logs for trigger reason. Manual reset:
```python
bot.risk_manager.deactivate_circuit_breaker()
```

**5. Low confidence signals**

Possible causes:
- Indicators disagree (normal in ranging market)
- Timeframe conflict
- Adjust weights in `config.yaml` if needed

## Performance Optimization

### Reducing Latency

1. Use limit orders instead of market orders
2. Optimize `refresh_interval` (balance: reactivity vs rate limits)
3. Use WebSocket for real-time price (TODO: not yet implemented)

### Memory Usage

- Adjust `data.max_cache_size` in config
- Reduce `data.lookback_periods` if RAM-constrained

## Disclaimer

**IMPORTANT**: This bot trades with real money and leverage. Use at your own risk.

- Always start with paper trading
- Never risk more than you can afford to lose
- Leverage amplifies both gains AND losses
- Past performance does not guarantee future results
- The authors are not responsible for any financial losses

## License

MIT License - See LICENSE file for details

## Support

For issues, questions, or contributions, please open an issue on GitHub.

## Roadmap

- [ ] WebSocket support for real-time data
- [ ] Additional exchanges (Binance, Bybit)
- [ ] Machine learning signal enhancement
- [ ] Advanced order types (trailing stop, iceberg)
- [ ] Web dashboard for monitoring
- [ ] Telegram bot for notifications
- [ ] Multi-pair support
- [ ] Dynamic leverage adjustment
- [ ] Portfolio rebalancing

---

**Built with ❤️ for scalpers by scalpers**
