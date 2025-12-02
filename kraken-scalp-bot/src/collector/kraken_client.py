"""
Kraken API Client for OHLCV data collection and order execution
"""
import asyncio
import hashlib
import hmac
import time
import urllib.parse
from base64 import b64decode, b64encode
from typing import Dict, List, Optional, Any
import aiohttp
import logging

logger = logging.getLogger(__name__)


class KrakenClient:
    """Async Kraken API client for REST endpoints"""

    BASE_URL = "https://api.kraken.com"
    API_VERSION = "0"

    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None):
        """
        Initialize Kraken client

        Args:
            api_key: Kraken API key (required for private endpoints)
            api_secret: Kraken API secret (required for private endpoints)
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    def _get_kraken_signature(self, urlpath: str, data: Dict[str, Any], nonce: str) -> str:
        """
        Generate Kraken API signature

        Args:
            urlpath: API endpoint path
            data: Request data
            nonce: Request nonce

        Returns:
            Base64 encoded signature
        """
        postdata = urllib.parse.urlencode(data)
        encoded = (nonce + postdata).encode()
        message = urlpath.encode() + hashlib.sha256(encoded).digest()

        mac = hmac.new(b64decode(self.api_secret), message, hashlib.sha512)
        sigdigest = b64encode(mac.digest())
        return sigdigest.decode()

    async def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        private: bool = False
    ) -> Dict[str, Any]:
        """
        Make async request to Kraken API

        Args:
            method: HTTP method (GET/POST)
            endpoint: API endpoint
            data: Request data
            private: Whether this is a private endpoint

        Returns:
            API response dictionary

        Raises:
            Exception: On API errors
        """
        if not self.session:
            raise RuntimeError("Client session not initialized. Use async context manager.")

        url = f"{self.BASE_URL}/{self.API_VERSION}/{endpoint}"
        headers = {}

        if private:
            if not self.api_key or not self.api_secret:
                raise ValueError("API key and secret required for private endpoints")

            nonce = str(int(time.time() * 1000))
            data = data or {}
            data["nonce"] = nonce

            urlpath = f"/{self.API_VERSION}/{endpoint}"
            headers = {
                "API-Key": self.api_key,
                "API-Sign": self._get_kraken_signature(urlpath, data, nonce)
            }

        try:
            if method == "GET":
                async with self.session.get(url, params=data, headers=headers) as response:
                    result = await response.json()
            else:
                async with self.session.post(url, data=data, headers=headers) as response:
                    result = await response.json()

            if result.get("error"):
                raise Exception(f"Kraken API error: {result['error']}")

            return result.get("result", {})

        except aiohttp.ClientError as e:
            logger.error(f"HTTP request failed: {e}")
            raise

    async def get_ohlc(
        self,
        pair: str,
        interval: int = 1,
        since: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get OHLC data

        Args:
            pair: Asset pair (e.g., 'XBTUSD')
            interval: Time interval in minutes (1, 5, 15, 30, 60, 240, 1440, 10080, 21600)
            since: Return data since this timestamp

        Returns:
            OHLC data with format:
            {
                'pair_name': [[time, open, high, low, close, vwap, volume, count], ...],
                'last': last_timestamp
            }
        """
        data = {"pair": pair, "interval": interval}
        if since:
            data["since"] = since

        return await self._request("GET", "public/OHLC", data=data)

    async def get_asset_pairs(self, pair: Optional[str] = None) -> Dict[str, Any]:
        """
        Get tradable asset pair information
        IMPORTANT: Use this to verify:
        - Minimum order volume (ordermin)
        - Price precision (pair_decimals)
        - Volume precision (lot_decimals)
        - Margin trading availability (leverage_buy, leverage_sell)

        Args:
            pair: Specific pair to query (optional)

        Returns:
            Asset pair information
        """
        data = {}
        if pair:
            data["pair"] = pair

        return await self._request("GET", "public/AssetPairs", data=data)

    async def get_ticker(self, pair: str) -> Dict[str, Any]:
        """
        Get ticker information

        Args:
            pair: Asset pair

        Returns:
            Ticker data including best bid/ask
        """
        return await self._request("GET", "public/Ticker", data={"pair": pair})

    async def get_trade_balance(self, asset: str = "ZUSD") -> Dict[str, Any]:
        """
        Get account trade balance
        IMPORTANT: Use this to check:
        - Current equity (eb)
        - Available margin (mf - margin free)
        - Margin level (ml)
        - Total margin used (m)

        Args:
            asset: Base asset for balance (default: ZUSD)

        Returns:
            Trade balance information
        """
        return await self._request("POST", "private/TradeBalance", data={"asset": asset}, private=True)

    async def add_order(
        self,
        pair: str,
        type_: str,  # 'buy' or 'sell'
        ordertype: str,  # 'market', 'limit', etc.
        volume: float,
        price: Optional[float] = None,
        leverage: Optional[int] = None,
        oflags: Optional[str] = None,
        starttm: Optional[int] = None,
        expiretm: Optional[int] = None,
        userref: Optional[int] = None,
        validate: bool = False,
        close_ordertype: Optional[str] = None,
        close_price: Optional[float] = None,
        close_price2: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Add standard order

        Args:
            pair: Asset pair
            type_: Order type (buy/sell)
            ordertype: Order type (market/limit/stop-loss/take-profit/etc.)
            volume: Order volume in lots
            price: Price (required for limit orders)
            leverage: Amount of leverage (2, 3, 4, 5, etc.)
            oflags: Order flags (fcib, fciq, nompp, post)
            starttm: Scheduled start time
            expiretm: Expiration time
            userref: User reference ID (for tracking)
            validate: Validate only, don't submit
            close_ordertype: Conditional close order type
            close_price: Conditional close price
            close_price2: Conditional close price 2

        Returns:
            Order result with txid
        """
        data = {
            "pair": pair,
            "type": type_,
            "ordertype": ordertype,
            "volume": str(volume),
        }

        if price is not None:
            data["price"] = str(price)
        if leverage is not None:
            data["leverage"] = str(leverage)
        if oflags:
            data["oflags"] = oflags
        if starttm:
            data["starttm"] = str(starttm)
        if expiretm:
            data["expiretm"] = str(expiretm)
        if userref:
            data["userref"] = str(userref)
        if validate:
            data["validate"] = "true"
        if close_ordertype:
            data["close[ordertype]"] = close_ordertype
        if close_price is not None:
            data["close[price]"] = str(close_price)
        if close_price2 is not None:
            data["close[price2]"] = str(close_price2)

        return await self._request("POST", "private/AddOrder", data=data, private=True)

    async def cancel_order(self, txid: str) -> Dict[str, Any]:
        """
        Cancel open order

        Args:
            txid: Transaction ID

        Returns:
            Cancellation result
        """
        return await self._request("POST", "private/CancelOrder", data={"txid": txid}, private=True)

    async def get_open_orders(self, trades: bool = False, userref: Optional[int] = None) -> Dict[str, Any]:
        """
        Get open orders

        Args:
            trades: Whether to include trades
            userref: Filter by user reference ID

        Returns:
            Open orders
        """
        data = {"trades": str(trades).lower()}
        if userref:
            data["userref"] = str(userref)

        return await self._request("POST", "private/OpenOrders", data=data, private=True)

    async def get_closed_orders(
        self,
        trades: bool = False,
        userref: Optional[int] = None,
        start: Optional[int] = None,
        end: Optional[int] = None,
        ofs: Optional[int] = None,
        closetime: str = "both"
    ) -> Dict[str, Any]:
        """
        Get closed orders

        Args:
            trades: Whether to include trades
            userref: Filter by user reference ID
            start: Starting timestamp
            end: Ending timestamp
            ofs: Result offset
            closetime: Which time to use (open/close/both)

        Returns:
            Closed orders
        """
        data = {
            "trades": str(trades).lower(),
            "closetime": closetime
        }
        if userref:
            data["userref"] = str(userref)
        if start:
            data["start"] = str(start)
        if end:
            data["end"] = str(end)
        if ofs:
            data["ofs"] = str(ofs)

        return await self._request("POST", "private/ClosedOrders", data=data, private=True)
