// Dashboard JavaScript - Real-time updates with Socket.IO

let socket;
let isConnected = false;
let botRunning = false;

// Initialize Socket.IO connection
function initSocket() {
    socket = io();

    socket.on('connect', () => {
        console.log('Connected to server');
        isConnected = true;
        addLog('Connected to server', 'success');
    });

    socket.on('disconnect', () => {
        console.log('Disconnected from server');
        isConnected = false;
        addLog('Disconnected from server', 'error');
    });

    socket.on('initial_data', (data) => {
        console.log('Received initial data', data);
        updateAllData(data);
    });

    socket.on('ticker_update', (ticker) => {
        updateTicker(ticker);
    });

    socket.on('balance_update', (balance) => {
        updateBalance(balance);
    });

    socket.on('signal_update', (signal) => {
        updateSignal(signal);
    });

    socket.on('positions_update', (positions) => {
        updatePositions(positions);
    });

    socket.on('trade_update', (trade) => {
        addTrade(trade);
    });

    socket.on('log_update', (log) => {
        addLog(log.message, log.level);
    });

    socket.on('status_update', (status) => {
        updateStatus(status);
    });
}

// Update all data at once
function updateAllData(data) {
    if (data.ticker) updateTicker(data.ticker);
    if (data.balance) updateBalance(data.balance);
    if (data.current_signal) updateSignal(data.current_signal);
    if (data.positions) updatePositions(data.positions);
    if (data.trades) updateTrades(data.trades);
    if (data.logs) updateLogs(data.logs);
    if (data.status) {
        botRunning = data.status === 'running';
        updateBotControls();
    }
}

// Update ticker/price data
function updateTicker(ticker) {
    if (!ticker || !ticker.last) return;

    const price = ticker.last;
    const high = ticker.high;
    const low = ticker.low;
    const volume = ticker.volume;

    document.getElementById('btcPrice').textContent = `$${formatNumber(price)}`;
    document.getElementById('high24h').textContent = `$${formatNumber(high)}`;
    document.getElementById('low24h').textContent = `$${formatNumber(low)}`;
    document.getElementById('volume24h').textContent = `${formatNumber(volume)} BTC`;

    // Calculate price change
    const change = ((price - low) / low * 100).toFixed(2);
    const changeElement = document.getElementById('priceChange');
    changeElement.textContent = `${change > 0 ? '+' : ''}${change}%`;
    changeElement.className = `metric-change ${change >= 0 ? 'positive' : 'negative'}`;
}

// Update balance
function updateBalance(balance) {
    if (!balance) return;

    const usd = balance.ZUSD || 0;
    const btc = balance.XXBT || 0;

    // Get current BTC price for total value calculation
    const btcPriceText = document.getElementById('btcPrice').textContent;
    const btcPrice = parseFloat(btcPriceText.replace(/[$,]/g, '')) || 0;

    const totalValue = usd + (btc * btcPrice);

    document.getElementById('usdBalance').textContent = `$${formatNumber(usd)}`;
    document.getElementById('btcBalance').textContent = btc.toFixed(6);
    document.getElementById('totalValue').textContent = `$${formatNumber(totalValue)}`;
}

// Update trading signal
function updateSignal(signal) {
    if (!signal) return;

    const signalElement = document.getElementById('signalIndicator');
    const strengthElement = document.getElementById('signalStrength');
    const progressElement = document.getElementById('signalProgress');
    const reasonElement = document.getElementById('signalReason');

    // Update signal type
    const signalType = signal.signal.toUpperCase();
    let icon = '';
    let className = 'signal-indicator ';

    if (signalType === 'BUY') {
        icon = '<i class="fas fa-arrow-up"></i> ';
        className += 'signal-buy';
        progressElement.className = 'progress-bar bg-success';
    } else if (signalType === 'SELL') {
        icon = '<i class="fas fa-arrow-down"></i> ';
        className += 'signal-sell';
        progressElement.className = 'progress-bar bg-danger';
    } else {
        icon = '<i class="fas fa-minus-circle"></i> ';
        className += 'signal-hold';
        progressElement.className = 'progress-bar bg-warning';
    }

    signalElement.className = className;
    signalElement.innerHTML = icon + signalType;

    // Update strength
    const strength = signal.strength || 0;
    strengthElement.textContent = `${strength.toFixed(1)}%`;
    progressElement.style.width = `${strength}%`;

    // Update reason
    reasonElement.textContent = signal.reason || 'No reason provided';

    // Update indicators
    if (signal.indicators) {
        const ind = signal.indicators;
        document.getElementById('ind_rsi').textContent = ind.rsi || '--';
        document.getElementById('ind_macd').textContent = ind.macd ? ind.macd.toFixed(2) : '--';
        document.getElementById('ind_ema_short').textContent = ind.ema_short ? `$${formatNumber(ind.ema_short)}` : '--';
        document.getElementById('ind_ema_medium').textContent = ind.ema_medium ? `$${formatNumber(ind.ema_medium)}` : '--';
        document.getElementById('ind_ema_long').textContent = ind.ema_long ? `$${formatNumber(ind.ema_long)}` : '--';
        document.getElementById('ind_stoch').textContent = ind.stoch_k ? ind.stoch_k.toFixed(1) : '--';
        document.getElementById('ind_bb_upper').textContent = ind.bb_upper ? `$${formatNumber(ind.bb_upper)}` : '--';
        document.getElementById('ind_bb_lower').textContent = ind.bb_lower ? `$${formatNumber(ind.bb_lower)}` : '--';
        document.getElementById('ind_volume').textContent = ind.volume_ratio ? `${ind.volume_ratio.toFixed(2)}x` : '--';
        document.getElementById('ind_atr').textContent = ind.atr ? `$${ind.atr.toFixed(2)}` : '--';
    }
}

// Update positions
function updatePositions(positions) {
    const container = document.getElementById('positionsContainer');
    const positionCount = document.getElementById('openPositions');

    if (!positions || Object.keys(positions).length === 0) {
        container.innerHTML = '<p class="text-secondary text-center">No open positions</p>';
        positionCount.textContent = '0';
        return;
    }

    const count = Object.keys(positions).length;
    positionCount.textContent = count;

    let html = '<table class="table table-sm"><thead><tr><th>Type</th><th>Size</th><th>P&L</th></tr></thead><tbody>';

    for (const [id, pos] of Object.entries(positions)) {
        const pnl = parseFloat(pos.net || 0) * 100;
        const pnlClass = pnl >= 0 ? 'positive' : 'negative';

        html += `
            <tr>
                <td><span class="badge ${pos.type === 'buy' ? 'bg-success' : 'bg-danger'}">${pos.type.toUpperCase()}</span></td>
                <td>${pos.vol} BTC</td>
                <td class="${pnlClass}">${pnl >= 0 ? '+' : ''}${pnl.toFixed(2)}%</td>
            </tr>
        `;
    }

    html += '</tbody></table>';
    container.innerHTML = html;
}

// Update trades list
function updateTrades(trades) {
    if (!trades || trades.length === 0) return;

    const container = document.getElementById('tradesContainer');
    let html = '<table class="table table-sm"><thead><tr><th>Time</th><th>Side</th><th>Price</th><th>Strength</th></tr></thead><tbody>';

    trades.slice(0, 5).forEach(trade => {
        const time = new Date(trade.timestamp).toLocaleTimeString();
        const sideClass = trade.side === 'buy' ? 'bg-success' : 'bg-danger';

        html += `
            <tr>
                <td>${time}</td>
                <td><span class="badge ${sideClass}">${trade.side.toUpperCase()}</span></td>
                <td>$${formatNumber(trade.price)}</td>
                <td>${trade.signal_strength?.toFixed(1) || '--'}%</td>
            </tr>
        `;
    });

    html += '</tbody></table>';
    container.innerHTML = html;
}

// Add single trade
function addTrade(trade) {
    // Add flash notification
    addLog(`New trade executed: ${trade.side.toUpperCase()} at $${formatNumber(trade.price)}`, 'success');
}

// Update logs
function updateLogs(logs) {
    const container = document.getElementById('logsContainer');
    container.innerHTML = '';

    logs.forEach(log => {
        addLogElement(log.time, log.message, log.level);
    });
}

// Add single log entry
function addLog(message, level = 'info') {
    const now = new Date();
    const time = now.toLocaleTimeString();
    addLogElement(time, message, level);
}

// Add log element to DOM
function addLogElement(time, message, level) {
    const container = document.getElementById('logsContainer');
    const entry = document.createElement('div');
    entry.className = 'log-entry';

    entry.innerHTML = `
        <span class="log-time">${time}</span>
        <span class="log-${level}">${message}</span>
    `;

    // Insert at the beginning
    if (container.firstChild) {
        container.insertBefore(entry, container.firstChild);
    } else {
        container.appendChild(entry);
    }

    // Keep only last 50 logs
    while (container.children.length > 50) {
        container.removeChild(container.lastChild);
    }
}

// Update status
function updateStatus(status) {
    if (status.iterations !== undefined) {
        document.getElementById('iterations').textContent = status.iterations;
    }

    if (status.status) {
        botRunning = status.status === 'running';
        updateBotControls();
    }
}

// Update bot control buttons
function updateBotControls() {
    const statusBadge = document.getElementById('statusBadge');
    const statusText = document.getElementById('statusText');
    const startBtn = document.getElementById('startBtn');
    const stopBtn = document.getElementById('stopBtn');

    if (botRunning) {
        statusBadge.className = 'status-badge status-running';
        statusText.textContent = 'Running';
        startBtn.disabled = true;
        stopBtn.disabled = false;
    } else {
        statusBadge.className = 'status-badge status-stopped';
        statusText.textContent = 'Stopped';
        startBtn.disabled = false;
        stopBtn.disabled = true;
    }
}

// Start bot
async function startBot() {
    try {
        const response = await fetch('/api/start', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        const data = await response.json();

        if (data.status === 'success') {
            addLog('Bot started successfully', 'success');
            botRunning = true;
            updateBotControls();
        } else {
            addLog(`Failed to start bot: ${data.message}`, 'error');
            alert(`Error: ${data.message}`);
        }
    } catch (error) {
        addLog(`Error starting bot: ${error.message}`, 'error');
        alert(`Error: ${error.message}`);
    }
}

// Stop bot
async function stopBot() {
    if (!confirm('Are you sure you want to stop the trading bot?')) {
        return;
    }

    try {
        const response = await fetch('/api/stop', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        const data = await response.json();

        if (data.status === 'success') {
            addLog('Bot stopped', 'warning');
            botRunning = false;
            updateBotControls();
        } else {
            addLog(`Failed to stop bot: ${data.message}`, 'error');
        }
    } catch (error) {
        addLog(`Error stopping bot: ${error.message}`, 'error');
    }
}

// Refresh data
function refreshData() {
    if (socket && socket.connected) {
        socket.emit('request_update');
        addLog('Refreshing data...', 'info');
    } else {
        addLog('Not connected to server', 'error');
    }
}

// Format number with commas
function formatNumber(num) {
    if (num === null || num === undefined) return '0';
    return parseFloat(num).toLocaleString('en-US', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    initSocket();
    updateBotControls();

    // Auto-refresh every 30 seconds
    setInterval(() => {
        if (!botRunning && socket && socket.connected) {
            socket.emit('request_update');
        }
    }, 30000);
});
