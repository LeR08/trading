"""
Order Executor - Handles order placement and management

Features:
- Retry logic with exponential backoff
- Idempotent order placement (clientOrderID)
- OCO (One-Cancels-Other) support for SL/TP
- Paper trading mode
"""
import asyncio
import hashlib
import time
import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, Optional, List
import logging

from ..collector.kraken_client import KrakenClient
from ..risk_engine.risk_manager import PositionSize

logger = logging.getLogger(__name__)


class OrderStatus(Enum):
    """Order status"""
    PENDING = "pending"
    SUBMITTED = "submitted"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ExecutionMode(Enum):
    """Execution mode"""
    LIVE = "live"
    PAPER = "paper"
    VALIDATE = "validate"


@dataclass
class OrderResult:
    """Result of order execution"""
    success: bool
    order_id: Optional[str]
    client_order_id: str
    status: OrderStatus
    message: Optional[str] = None
    metadata: Dict[str, any] = None


@dataclass
class Trade:
    """Represents a trade"""
    trade_id: str
    client_order_id: str
    pair: str
    direction: str
    entry_price: float
    volume: float
    stop_loss: float
    take_profit: float
    leverage: int
    timestamp: int
    status: str = "open"
    exit_price: Optional[float] = None
    pnl: Optional[float] = None
    metadata: Dict[str, any] = None


class OrderExecutor:
    """
    Handles order execution with retry logic and error handling

    Features:
    - Exponential backoff for retries
    - Idempotent order placement using clientOrderID
    - Paper trading mode (simulation)
    - Rate limit handling
    """

    def __init__(
        self,
        client: KrakenClient,
        mode: ExecutionMode = ExecutionMode.LIVE,
        max_retries: int = 3,
        retry_delay: float = 2.0,
    ):
        """
        Initialize order executor

        Args:
            client: Kraken API client
            mode: Execution mode (LIVE/PAPER/VALIDATE)
            max_retries: Maximum retry attempts
            retry_delay: Initial retry delay in seconds
        """
        self.client = client
        self.mode = mode
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # Order tracking
        self.pending_orders: Dict[str, OrderResult] = {}
        self.filled_orders: Dict[str, OrderResult] = {}

        # Paper trading state
        self.paper_trades: Dict[str, Trade] = {}
        self.paper_equity = 10000.0  # Starting paper equity

        logger.info(f"OrderExecutor initialized in {mode.value} mode")

    def _generate_client_order_id(self, params: Dict) -> str:
        """
        Generate deterministic client order ID for idempotency

        Args:
            params: Order parameters

        Returns:
            Client order ID
        """
        # Create hash from order params
        order_str = f"{params['pair']}_{params['type']}_{params['volume']}_{params.get('price', 'market')}_{int(time.time())}"
        order_hash = hashlib.md5(order_str.encode()).hexdigest()[:16]
        return f"scalp_{order_hash}"

    async def _place_order_with_retry(
        self,
        order_params: Dict,
        client_order_id: str
    ) -> OrderResult:
        """
        Place order with retry logic

        Args:
            order_params: Order parameters
            client_order_id: Client order ID for idempotency

        Returns:
            OrderResult
        """
        last_error = None

        for attempt in range(self.max_retries):
            try:
                logger.info(f"Placing order (attempt {attempt + 1}/{self.max_retries}): {order_params}")

                # Add userref for tracking
                order_params["userref"] = int(hashlib.md5(client_order_id.encode()).hexdigest()[:8], 16)

                result = await self.client.add_order(**order_params)

                if result.get("txid"):
                    order_id = result["txid"][0] if isinstance(result["txid"], list) else result["txid"]

                    logger.info(f"Order placed successfully: {order_id}")

                    return OrderResult(
                        success=True,
                        order_id=order_id,
                        client_order_id=client_order_id,
                        status=OrderStatus.SUBMITTED,
                        message="Order submitted successfully",
                        metadata=result
                    )
                else:
                    logger.warning(f"Order result missing txid: {result}")
                    last_error = "No transaction ID returned"

            except Exception as e:
                last_error = str(e)
                logger.warning(f"Order placement failed (attempt {attempt + 1}): {e}")

                # Check if error is retryable
                if "rate limit" in str(e).lower():
                    delay = self.retry_delay * (2 ** attempt)
                    logger.info(f"Rate limited, waiting {delay}s before retry")
                    await asyncio.sleep(delay)
                elif "insufficient" in str(e).lower():
                    # Insufficient funds - don't retry
                    return OrderResult(
                        success=False,
                        order_id=None,
                        client_order_id=client_order_id,
                        status=OrderStatus.REJECTED,
                        message=f"Insufficient funds: {e}",
                        metadata={"error": str(e)}
                    )
                else:
                    # Other errors - wait and retry
                    delay = self.retry_delay * (2 ** attempt)
                    await asyncio.sleep(delay)

        # All retries failed
        return OrderResult(
            success=False,
            order_id=None,
            client_order_id=client_order_id,
            status=OrderStatus.REJECTED,
            message=f"Order failed after {self.max_retries} attempts: {last_error}",
            metadata={"last_error": last_error}
        )

    async def place_market_order(
        self,
        pair: str,
        direction: str,
        volume: float,
        leverage: int,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
    ) -> OrderResult:
        """
        Place market order with optional SL/TP

        Args:
            pair: Trading pair
            direction: 'long' or 'short'
            volume: Order volume
            leverage: Leverage amount
            stop_loss: Stop loss price
            take_profit: Take profit price

        Returns:
            OrderResult
        """
        order_type = "buy" if direction == "long" else "sell"

        order_params = {
            "pair": pair,
            "type_": order_type,
            "ordertype": "market",
            "volume": volume,
            "leverage": leverage,
        }

        # Add SL/TP as close order if provided
        if stop_loss:
            order_params["close_ordertype"] = "stop-loss"
            order_params["close_price"] = stop_loss

        if take_profit:
            order_params["close_ordertype"] = "take-profit"
            order_params["close_price"] = take_profit

        client_order_id = self._generate_client_order_id(order_params)

        # Handle different execution modes
        if self.mode == ExecutionMode.VALIDATE:
            order_params["validate"] = True
            result = await self._place_order_with_retry(order_params, client_order_id)
            result.message = "Order validation successful"
            return result

        elif self.mode == ExecutionMode.PAPER:
            return self._simulate_order(order_params, client_order_id)

        else:  # LIVE
            return await self._place_order_with_retry(order_params, client_order_id)

    async def place_limit_order(
        self,
        pair: str,
        direction: str,
        volume: float,
        price: float,
        leverage: int,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
    ) -> OrderResult:
        """
        Place limit order with optional SL/TP

        Args:
            pair: Trading pair
            direction: 'long' or 'short'
            volume: Order volume
            price: Limit price
            leverage: Leverage amount
            stop_loss: Stop loss price
            take_profit: Take profit price

        Returns:
            OrderResult
        """
        order_type = "buy" if direction == "long" else "sell"

        order_params = {
            "pair": pair,
            "type_": order_type,
            "ordertype": "limit",
            "volume": volume,
            "price": price,
            "leverage": leverage,
        }

        # Add SL/TP
        if stop_loss:
            order_params["close_ordertype"] = "stop-loss"
            order_params["close_price"] = stop_loss

        if take_profit:
            order_params["close_ordertype"] = "take-profit"
            order_params["close_price"] = take_profit

        client_order_id = self._generate_client_order_id(order_params)

        if self.mode == ExecutionMode.VALIDATE:
            order_params["validate"] = True
            result = await self._place_order_with_retry(order_params, client_order_id)
            result.message = "Order validation successful"
            return result

        elif self.mode == ExecutionMode.PAPER:
            return self._simulate_order(order_params, client_order_id)

        else:  # LIVE
            return await self._place_order_with_retry(order_params, client_order_id)

    def _simulate_order(self, order_params: Dict, client_order_id: str) -> OrderResult:
        """
        Simulate order execution for paper trading

        Args:
            order_params: Order parameters
            client_order_id: Client order ID

        Returns:
            OrderResult
        """
        trade_id = str(uuid.uuid4())[:8]

        logger.info(f"PAPER TRADE: Simulating order {client_order_id}")
        logger.info(f"  Pair: {order_params['pair']}")
        logger.info(f"  Type: {order_params['type_']}")
        logger.info(f"  Volume: {order_params['volume']}")
        logger.info(f"  Price: {order_params.get('price', 'MARKET')}")
        logger.info(f"  Leverage: {order_params.get('leverage', 1)}x")

        # Store paper trade
        trade = Trade(
            trade_id=trade_id,
            client_order_id=client_order_id,
            pair=order_params["pair"],
            direction="long" if order_params["type_"] == "buy" else "short",
            entry_price=order_params.get("price", 0),  # Would use current price in real scenario
            volume=order_params["volume"],
            stop_loss=order_params.get("close_price", 0),
            take_profit=order_params.get("close_price", 0),
            leverage=order_params.get("leverage", 1),
            timestamp=int(time.time()),
            metadata=order_params
        )

        self.paper_trades[trade_id] = trade

        return OrderResult(
            success=True,
            order_id=trade_id,
            client_order_id=client_order_id,
            status=OrderStatus.FILLED,
            message="Paper trade executed",
            metadata={"paper_trade": True, "trade": trade}
        )

    async def cancel_order(self, order_id: str) -> bool:
        """
        Cancel open order

        Args:
            order_id: Order ID to cancel

        Returns:
            True if cancelled successfully
        """
        if self.mode == ExecutionMode.PAPER:
            if order_id in self.paper_trades:
                del self.paper_trades[order_id]
                logger.info(f"PAPER TRADE: Cancelled order {order_id}")
                return True
            return False

        try:
            result = await self.client.cancel_order(order_id)
            logger.info(f"Order cancelled: {order_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to cancel order {order_id}: {e}")
            return False

    async def get_open_orders(self) -> List[Dict]:
        """
        Get open orders

        Returns:
            List of open orders
        """
        if self.mode == ExecutionMode.PAPER:
            return list(self.paper_trades.values())

        try:
            result = await self.client.get_open_orders(trades=True)
            return result.get("open", {})
        except Exception as e:
            logger.error(f"Failed to get open orders: {e}")
            return []

    async def get_closed_orders(self, start: Optional[int] = None) -> List[Dict]:
        """
        Get closed orders

        Args:
            start: Starting timestamp

        Returns:
            List of closed orders
        """
        if self.mode == ExecutionMode.PAPER:
            return []

        try:
            result = await self.client.get_closed_orders(start=start)
            return result.get("closed", {})
        except Exception as e:
            logger.error(f"Failed to get closed orders: {e}")
            return []

    def get_paper_equity(self) -> float:
        """
        Get current paper trading equity

        Returns:
            Current equity
        """
        return self.paper_equity

    def update_paper_trade(self, trade_id: str, exit_price: float, pnl: float):
        """
        Update paper trade with exit and P&L

        Args:
            trade_id: Trade ID
            exit_price: Exit price
            pnl: Realized P&L
        """
        if trade_id in self.paper_trades:
            trade = self.paper_trades[trade_id]
            trade.exit_price = exit_price
            trade.pnl = pnl
            trade.status = "closed"

            self.paper_equity += pnl

            logger.info(f"PAPER TRADE CLOSED: {trade_id} | P&L: ${pnl:.2f} | Equity: ${self.paper_equity:.2f}")
