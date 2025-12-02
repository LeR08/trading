"""
Web API for bot control and monitoring
"""
from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, List
import asyncio
import json
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class BotConfig(BaseModel):
    """Bot configuration model"""
    mode: str  # paper, validate, live
    confidence_threshold: float
    risk_per_trade: float
    max_concurrent_trades: int
    leverage: int


class BotStatus(BaseModel):
    """Bot status model"""
    running: bool
    mode: str
    iteration: int
    equity: float
    margin_free: float
    margin_used: float
    open_positions: int
    daily_pnl: float
    total_pnl: float
    circuit_breaker_active: bool


class Trade(BaseModel):
    """Trade model"""
    id: str
    direction: str
    entry_price: float
    volume: float
    stop_loss: float
    take_profit: float
    current_pnl: Optional[float] = None
    timestamp: str


class WebAPI:
    """Web API for bot control"""

    def __init__(self, bot):
        """
        Initialize web API

        Args:
            bot: KrakenScalpBot instance
        """
        self.bot = bot
        self.app = FastAPI(title="Kraken Scalp Bot API", version="1.0.0")

        # CORS
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # WebSocket connections
        self.ws_connections: List[WebSocket] = []

        # Setup routes
        self._setup_routes()

    def _setup_routes(self):
        """Setup API routes"""

        @self.app.get("/")
        async def root():
            """Serve dashboard"""
            return HTMLResponse(content=self._get_dashboard_html())

        @self.app.get("/api/status")
        async def get_status():
            """Get bot status"""
            try:
                trade_balance = await self.bot.client.get_trade_balance() if self.bot.config.execution_mode != "paper" else {}

                equity = float(trade_balance.get("e", 0)) if trade_balance else self.bot.executor.paper_equity
                margin_free = float(trade_balance.get("mf", 0)) if trade_balance else equity * 0.8
                margin_used = float(trade_balance.get("m", 0)) if trade_balance else 0

                status = BotStatus(
                    running=self.bot.running,
                    mode=self.bot.config.execution_mode,
                    iteration=self.bot.iteration,
                    equity=equity,
                    margin_free=margin_free,
                    margin_used=margin_used,
                    open_positions=len(self.bot.executor.paper_trades) if self.bot.config.execution_mode == "paper" else 0,
                    daily_pnl=self.bot.risk_manager.daily_pnl,
                    total_pnl=self.bot.risk_manager.total_pnl,
                    circuit_breaker_active=self.bot.risk_manager.circuit_breaker_active
                )

                return status

            except Exception as e:
                logger.error(f"Error getting status: {e}")
                return JSONResponse(status_code=500, content={"error": str(e)})

        @self.app.get("/api/trades")
        async def get_trades():
            """Get open trades"""
            try:
                trades = []

                if self.bot.config.execution_mode == "paper":
                    for trade_id, trade in self.bot.executor.paper_trades.items():
                        trades.append(Trade(
                            id=trade.trade_id,
                            direction=trade.direction,
                            entry_price=trade.entry_price,
                            volume=trade.volume,
                            stop_loss=trade.stop_loss,
                            take_profit=trade.take_profit,
                            current_pnl=trade.pnl,
                            timestamp=datetime.fromtimestamp(trade.timestamp, tz=timezone.utc).isoformat()
                        ))

                return trades

            except Exception as e:
                logger.error(f"Error getting trades: {e}")
                return JSONResponse(status_code=500, content={"error": str(e)})

        @self.app.post("/api/config")
        async def update_config(config: BotConfig):
            """Update bot configuration"""
            try:
                # Update config
                self.bot.config._config['trading']['mode'] = config.mode
                self.bot.config._config['signal']['confidence_threshold'] = config.confidence_threshold
                self.bot.config._config['risk']['risk_per_trade'] = config.risk_per_trade
                self.bot.config._config['risk']['max_concurrent_trades'] = config.max_concurrent_trades
                self.bot.config._config['trading']['leverage'] = config.leverage

                # Update components
                self.bot.signal_generator.confidence_threshold = config.confidence_threshold * 100
                self.bot.risk_manager.risk_per_trade = config.risk_per_trade
                self.bot.risk_manager.max_concurrent_trades = config.max_concurrent_trades
                self.bot.risk_manager.leverage = config.leverage

                logger.info(f"Configuration updated: {config}")

                return {"status": "success", "message": "Configuration updated"}

            except Exception as e:
                logger.error(f"Error updating config: {e}")
                return JSONResponse(status_code=500, content={"error": str(e)})

        @self.app.post("/api/start")
        async def start_bot():
            """Start bot"""
            if not self.bot.running:
                asyncio.create_task(self.bot.run())
                return {"status": "success", "message": "Bot started"}
            return {"status": "warning", "message": "Bot already running"}

        @self.app.post("/api/stop")
        async def stop_bot():
            """Stop bot"""
            if self.bot.running:
                self.bot.stop()
                return {"status": "success", "message": "Bot stopped"}
            return {"status": "warning", "message": "Bot not running"}

        @self.app.post("/api/circuit-breaker/reset")
        async def reset_circuit_breaker():
            """Reset circuit breaker"""
            self.bot.risk_manager.deactivate_circuit_breaker()
            return {"status": "success", "message": "Circuit breaker reset"}

        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket endpoint for real-time updates"""
            await websocket.accept()
            self.ws_connections.append(websocket)

            try:
                while True:
                    # Keep connection alive
                    await websocket.receive_text()
            except:
                self.ws_connections.remove(websocket)

    async def broadcast_update(self, data: Dict):
        """Broadcast update to all WebSocket connections"""
        for ws in self.ws_connections:
            try:
                await ws.send_json(data)
            except:
                self.ws_connections.remove(ws)

    def _get_dashboard_html(self) -> str:
        """Get dashboard HTML"""
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Kraken Scalp Bot Dashboard</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
        }

        .header {
            background: white;
            padding: 20px 30px;
            border-radius: 15px;
            margin-bottom: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        h1 {
            color: #667eea;
            font-size: 28px;
        }

        .mode-selector {
            display: flex;
            gap: 10px;
            align-items: center;
        }

        .mode-btn {
            padding: 10px 20px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 600;
            transition: all 0.3s;
        }

        .mode-btn.paper {
            background: #48bb78;
            color: white;
        }

        .mode-btn.live {
            background: #f56565;
            color: white;
        }

        .mode-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
        }

        .mode-btn.active {
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.4);
        }

        .controls {
            display: flex;
            gap: 10px;
        }

        .btn {
            padding: 10px 20px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 600;
            transition: all 0.3s;
        }

        .btn-start {
            background: #48bb78;
            color: white;
        }

        .btn-stop {
            background: #f56565;
            color: white;
        }

        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
        }

        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }

        .card {
            background: white;
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }

        .card h2 {
            color: #4a5568;
            font-size: 16px;
            margin-bottom: 15px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        .metric {
            font-size: 32px;
            font-weight: 700;
            color: #2d3748;
        }

        .metric.positive {
            color: #48bb78;
        }

        .metric.negative {
            color: #f56565;
        }

        .status-badge {
            display: inline-block;
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 14px;
            font-weight: 600;
        }

        .status-running {
            background: #48bb78;
            color: white;
        }

        .status-stopped {
            background: #cbd5e0;
            color: #4a5568;
        }

        .trades-table {
            width: 100%;
            background: white;
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }

        table {
            width: 100%;
            border-collapse: collapse;
        }

        th {
            background: #f7fafc;
            padding: 15px;
            text-align: left;
            font-weight: 600;
            color: #4a5568;
            border-bottom: 2px solid #e2e8f0;
        }

        td {
            padding: 15px;
            border-bottom: 1px solid #e2e8f0;
        }

        .direction-long {
            color: #48bb78;
            font-weight: 600;
        }

        .direction-short {
            color: #f56565;
            font-weight: 600;
        }

        .config-section {
            background: white;
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            margin-bottom: 20px;
        }

        .config-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-top: 15px;
        }

        .input-group {
            display: flex;
            flex-direction: column;
        }

        .input-group label {
            font-size: 14px;
            color: #4a5568;
            margin-bottom: 8px;
            font-weight: 600;
        }

        .input-group input {
            padding: 10px;
            border: 2px solid #e2e8f0;
            border-radius: 8px;
            font-size: 16px;
        }

        .input-group input:focus {
            outline: none;
            border-color: #667eea;
        }

        .update-btn {
            background: #667eea;
            color: white;
            padding: 12px 30px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 600;
            margin-top: 15px;
        }

        .circuit-breaker {
            background: #fed7d7;
            padding: 15px;
            border-radius: 8px;
            margin-top: 15px;
            display: none;
        }

        .circuit-breaker.active {
            display: block;
        }

        .reset-btn {
            background: #f56565;
            color: white;
            padding: 8px 16px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            margin-left: 10px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 Kraken Scalp Bot</h1>
            <div class="mode-selector">
                <button class="mode-btn paper active" onclick="setMode('paper')">📝 Paper</button>
                <button class="mode-btn live" onclick="setMode('live')">🔴 Live</button>
            </div>
            <div class="controls">
                <button class="btn btn-start" onclick="startBot()">▶️ Start</button>
                <button class="btn btn-stop" onclick="stopBot()">⏹️ Stop</button>
            </div>
        </div>

        <div class="grid">
            <div class="card">
                <h2>Status</h2>
                <span id="status" class="status-badge status-stopped">Stopped</span>
                <div style="margin-top: 10px; font-size: 14px; color: #718096;">
                    Iteration: <span id="iteration">0</span>
                </div>
            </div>

            <div class="card">
                <h2>Equity</h2>
                <div class="metric" id="equity">$0.00</div>
            </div>

            <div class="card">
                <h2>Margin Free</h2>
                <div class="metric" id="margin-free">$0.00</div>
            </div>

            <div class="card">
                <h2>Open Positions</h2>
                <div class="metric" id="open-positions">0</div>
            </div>

            <div class="card">
                <h2>Daily P&L</h2>
                <div class="metric" id="daily-pnl">$0.00</div>
            </div>

            <div class="card">
                <h2>Total P&L</h2>
                <div class="metric" id="total-pnl">$0.00</div>
            </div>
        </div>

        <div class="circuit-breaker" id="circuit-breaker">
            ⚠️ Circuit Breaker Active
            <button class="reset-btn" onclick="resetCircuitBreaker()">Reset</button>
        </div>

        <div class="config-section">
            <h2>Configuration (Aggressive Mode)</h2>
            <div class="config-grid">
                <div class="input-group">
                    <label>Confidence Threshold (%)</label>
                    <input type="number" id="confidence" value="50" step="1" min="1" max="100">
                </div>
                <div class="input-group">
                    <label>Risk Per Trade (%)</label>
                    <input type="number" id="risk-per-trade" value="2" step="0.1" min="0.1" max="10">
                </div>
                <div class="input-group">
                    <label>Max Concurrent Trades</label>
                    <input type="number" id="max-trades" value="5" step="1" min="1" max="10">
                </div>
                <div class="input-group">
                    <label>Leverage</label>
                    <input type="number" id="leverage" value="3" step="1" min="1" max="10">
                </div>
            </div>
            <button class="update-btn" onclick="updateConfig()">Update Configuration</button>
        </div>

        <div class="trades-table">
            <h2>Open Trades</h2>
            <table>
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Direction</th>
                        <th>Entry</th>
                        <th>Volume</th>
                        <th>Stop Loss</th>
                        <th>Take Profit</th>
                        <th>P&L</th>
                        <th>Time</th>
                    </tr>
                </thead>
                <tbody id="trades-body">
                    <tr>
                        <td colspan="8" style="text-align: center; color: #a0aec0;">No open trades</td>
                    </tr>
                </tbody>
            </table>
        </div>
    </div>

    <script>
        let currentMode = 'paper';
        let ws = null;

        // Connect WebSocket
        function connectWebSocket() {
            ws = new WebSocket(`ws://${window.location.host}/ws`);

            ws.onmessage = function(event) {
                const data = JSON.parse(event.data);
                updateDashboard(data);
            };

            ws.onclose = function() {
                setTimeout(connectWebSocket, 3000);
            };
        }

        // Update dashboard
        async function updateStatus() {
            try {
                const response = await fetch('/api/status');
                const data = await response.json();

                document.getElementById('status').className = 'status-badge ' + (data.running ? 'status-running' : 'status-stopped');
                document.getElementById('status').textContent = data.running ? 'Running' : 'Stopped';
                document.getElementById('iteration').textContent = data.iteration;
                document.getElementById('equity').textContent = '$' + data.equity.toFixed(2);
                document.getElementById('margin-free').textContent = '$' + data.margin_free.toFixed(2);
                document.getElementById('open-positions').textContent = data.open_positions;

                const dailyPnl = document.getElementById('daily-pnl');
                dailyPnl.textContent = '$' + data.daily_pnl.toFixed(2);
                dailyPnl.className = 'metric ' + (data.daily_pnl >= 0 ? 'positive' : 'negative');

                const totalPnl = document.getElementById('total-pnl');
                totalPnl.textContent = '$' + data.total_pnl.toFixed(2);
                totalPnl.className = 'metric ' + (data.total_pnl >= 0 ? 'positive' : 'negative');

                document.getElementById('circuit-breaker').className = 'circuit-breaker ' + (data.circuit_breaker_active ? 'active' : '');

            } catch (error) {
                console.error('Error updating status:', error);
            }
        }

        async function updateTrades() {
            try {
                const response = await fetch('/api/trades');
                const trades = await response.json();

                const tbody = document.getElementById('trades-body');

                if (trades.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="8" style="text-align: center; color: #a0aec0;">No open trades</td></tr>';
                } else {
                    tbody.innerHTML = trades.map(trade => `
                        <tr>
                            <td>${trade.id.substring(0, 8)}</td>
                            <td class="direction-${trade.direction}">${trade.direction.toUpperCase()}</td>
                            <td>$${trade.entry_price.toFixed(2)}</td>
                            <td>${trade.volume.toFixed(8)}</td>
                            <td>$${trade.stop_loss.toFixed(2)}</td>
                            <td>$${trade.take_profit.toFixed(2)}</td>
                            <td class="${trade.current_pnl >= 0 ? 'direction-long' : 'direction-short'}">$${(trade.current_pnl || 0).toFixed(2)}</td>
                            <td>${new Date(trade.timestamp).toLocaleTimeString()}</td>
                        </tr>
                    `).join('');
                }

            } catch (error) {
                console.error('Error updating trades:', error);
            }
        }

        function setMode(mode) {
            currentMode = mode;
            document.querySelectorAll('.mode-btn').forEach(btn => btn.classList.remove('active'));
            document.querySelector(`.mode-btn.${mode}`).classList.add('active');
        }

        async function startBot() {
            const response = await fetch('/api/start', { method: 'POST' });
            const data = await response.json();
            alert(data.message);
        }

        async function stopBot() {
            const response = await fetch('/api/stop', { method: 'POST' });
            const data = await response.json();
            alert(data.message);
        }

        async function updateConfig() {
            const config = {
                mode: currentMode,
                confidence_threshold: parseFloat(document.getElementById('confidence').value) / 100,
                risk_per_trade: parseFloat(document.getElementById('risk-per-trade').value) / 100,
                max_concurrent_trades: parseInt(document.getElementById('max-trades').value),
                leverage: parseInt(document.getElementById('leverage').value)
            };

            const response = await fetch('/api/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(config)
            });

            const data = await response.json();
            alert(data.message);
        }

        async function resetCircuitBreaker() {
            const response = await fetch('/api/circuit-breaker/reset', { method: 'POST' });
            const data = await response.json();
            alert(data.message);
            updateStatus();
        }

        // Auto refresh
        setInterval(updateStatus, 2000);
        setInterval(updateTrades, 3000);

        // Initial load
        updateStatus();
        updateTrades();
        connectWebSocket();
    </script>
</body>
</html>
        """

    async def run(self, host: str = "0.0.0.0", port: int = 8080):
        """
        Run web server

        Args:
            host: Host to bind to
            port: Port to bind to
        """
        import uvicorn
        config = uvicorn.Config(self.app, host=host, port=port, log_level="info")
        server = uvicorn.Server(config)
        await server.serve()
