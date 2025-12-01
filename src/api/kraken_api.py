"""
Kraken API Client Module
Gère les appels REST API Kraken pour trading sur marge
"""
import os
import time
import hmac
import hashlib
import base64
import urllib.parse
import requests
from typing import Dict, Optional, Any
import logging

logger = logging.getLogger(__name__)


class KrakenAPI:
    """Client API Kraken avec support trading sur marge"""

    BASE_URL = "https://api.kraken.com"
    API_VERSION = "0"

    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None):
        """
        Initialise le client API Kraken

        Args:
            api_key: Clé API Kraken (ou depuis KRK_KEY env var)
            api_secret: Secret API Kraken (ou depuis KRK_SECRET env var)
        """
        self.api_key = api_key or os.getenv('KRK_KEY', '')
        self.api_secret = api_secret or os.getenv('KRK_SECRET', '')

        if not self.api_key or not self.api_secret:
            logger.warning("API credentials not provided. Only public endpoints available.")

    def _get_kraken_signature(self, urlpath: str, data: Dict, nonce: str) -> str:
        """
        Génère la signature HMAC-SHA512 pour authentification

        Args:
            urlpath: Chemin de l'endpoint API
            data: Données de la requête
            nonce: Nonce unique

        Returns:
            Signature encodée en base64
        """
        postdata = urllib.parse.urlencode(data)
        encoded = (str(nonce) + postdata).encode()
        message = urlpath.encode() + hashlib.sha256(encoded).digest()

        signature = hmac.new(
            base64.b64decode(self.api_secret),
            message,
            hashlib.sha512
        )
        return base64.b64encode(signature.digest()).decode()

    def _query_public(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """
        Effectue une requête publique (non authentifiée)

        Args:
            endpoint: Nom de l'endpoint (ex: 'AssetPairs', 'Ticker')
            params: Paramètres de la requête

        Returns:
            Réponse JSON de l'API
        """
        url = f"{self.BASE_URL}/{self.API_VERSION}/public/{endpoint}"

        try:
            response = requests.get(url, params=params or {}, timeout=30)
            response.raise_for_status()
            data = response.json()

            if data.get('error'):
                logger.error(f"Kraken API error: {data['error']}")

            return data

        except Exception as e:
            logger.error(f"Error querying public endpoint {endpoint}: {e}")
            return {'error': [str(e)]}

    def _query_private(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """
        Effectue une requête privée (authentifiée)

        Args:
            endpoint: Nom de l'endpoint (ex: 'AddOrder', 'TradeBalance')
            params: Paramètres de la requête

        Returns:
            Réponse JSON de l'API
        """
        if not self.api_key or not self.api_secret:
            return {'error': ['API credentials not configured']}

        urlpath = f"/{self.API_VERSION}/private/{endpoint}"
        url = f"{self.BASE_URL}{urlpath}"

        data = params or {}
        data['nonce'] = str(int(time.time() * 1000))

        headers = {
            'API-Key': self.api_key,
            'API-Sign': self._get_kraken_signature(urlpath, data, data['nonce'])
        }

        try:
            response = requests.post(url, headers=headers, data=data, timeout=30)
            response.raise_for_status()
            result = response.json()

            if result.get('error'):
                logger.error(f"Kraken API error: {result['error']}")

            return result

        except Exception as e:
            logger.error(f"Error querying private endpoint {endpoint}: {e}")
            return {'error': [str(e)]}

    # ==================== Public Endpoints ====================

    def get_asset_pairs(self, pair: Optional[str] = None) -> Dict:
        """
        Récupère les informations sur les paires d'actifs tradables
        IMPORTANT: Utiliser pour valider min/max qty, précisions, etc.

        Args:
            pair: Paire spécifique (ex: 'XBTEUR') ou None pour toutes

        Returns:
            Dict avec infos sur les paires (lot_decimals, pair_decimals, etc.)
        """
        params = {}
        if pair:
            params['pair'] = pair

        return self._query_public('AssetPairs', params)

    def get_ticker(self, pair: str) -> Dict:
        """
        Récupère les données ticker pour une paire

        Args:
            pair: Paire de trading (ex: 'XBTEUR')

        Returns:
            Dict avec prix ask/bid/last, volume, etc.
        """
        return self._query_public('Ticker', {'pair': pair})

    def get_ohlc(self, pair: str, interval: int = 60, since: Optional[int] = None) -> Dict:
        """
        Récupère les données OHLC (candlesticks)

        Args:
            pair: Paire de trading
            interval: Intervalle en minutes (1, 5, 15, 30, 60, 240, 1440, 10080, 21600)
            since: Timestamp depuis lequel récupérer les données

        Returns:
            Dict avec données OHLC
        """
        params = {'pair': pair, 'interval': interval}
        if since:
            params['since'] = since

        return self._query_public('OHLC', params)

    # ==================== Private Endpoints ====================

    def get_trade_balance(self, asset: str = 'ZUSD') -> Dict:
        """
        Récupère le solde de trading et informations sur la marge
        IMPORTANT: Utiliser pour vérifier collateral et margin level avant trading

        Args:
            asset: Asset de base pour calcul (ex: 'ZUSD', 'ZEUR')

        Returns:
            Dict avec:
            - eb: balance équivalente (combiné avec crédit de marge)
            - tb: balance de trading (équité)
            - m: marge utilisée dans positions ouvertes
            - n: marge utilisée dans ordres ouverts
            - c: coût total de positions ouvertes
            - v: valeur actuelle des positions ouvertes
            - e: équité = tb + v - c
            - mf: free margin = e - m - n
            - ml: margin level = (e / m) * 100 si m > 0
        """
        return self._query_private('TradeBalance', {'asset': asset})

    def get_open_orders(self) -> Dict:
        """
        Récupère tous les ordres ouverts

        Returns:
            Dict avec ordres ouverts
        """
        return self._query_private('OpenOrders')

    def get_open_positions(self, txid: Optional[str] = None, docalcs: bool = True) -> Dict:
        """
        Récupère les positions ouvertes sur marge

        Args:
            txid: ID de transaction spécifique (optionnel)
            docalcs: Inclure calculs P&L

        Returns:
            Dict avec positions ouvertes
        """
        params = {'docalcs': str(docalcs).lower()}
        if txid:
            params['txid'] = txid

        return self._query_private('OpenPositions', params)

    def add_order(
        self,
        pair: str,
        side: str,
        ordertype: str,
        volume: float,
        price: Optional[float] = None,
        price2: Optional[float] = None,
        leverage: Optional[int] = None,
        oflags: Optional[str] = None,
        timeinforce: Optional[str] = None,
        starttm: Optional[str] = None,
        expiretm: Optional[str] = None,
        close_ordertype: Optional[str] = None,
        close_price: Optional[float] = None,
        close_price2: Optional[float] = None,
        validate: bool = False
    ) -> Dict:
        """
        Place un ordre via /private/AddOrder

        Args:
            pair: Paire d'actifs (ex: 'XBTEUR')
            side: 'buy' ou 'sell'
            ordertype: Type d'ordre ('market', 'limit', 'stop-loss', etc.)
            volume: Volume à trader
            price: Prix limite (pour limit orders)
            price2: Prix secondaire (pour stop-loss-limit, etc.)
            leverage: Effet de levier (ex: 3 pour 3x)
            oflags: Flags optionnels (ex: 'fciq' pour fee in quote currency)
            timeinforce: 'GTC', 'IOC', 'GTD'
            starttm: Timestamp de début (scheduled orders)
            expiretm: Timestamp d'expiration
            close_ordertype: Type d'ordre de fermeture (pour take-profit/stop-loss)
            close_price: Prix de fermeture
            close_price2: Prix secondaire de fermeture
            validate: Si True, valide seulement sans placer l'ordre

        Returns:
            Dict avec résultat de l'ordre (txid, descr, etc.)
        """
        params = {
            'pair': pair,
            'type': side,
            'ordertype': ordertype,
            'volume': str(volume)
        }

        if price is not None:
            params['price'] = str(price)
        if price2 is not None:
            params['price2'] = str(price2)
        if leverage is not None:
            params['leverage'] = str(leverage)
        if oflags:
            params['oflags'] = oflags
        if timeinforce:
            params['timeinforce'] = timeinforce
        if starttm:
            params['starttm'] = starttm
        if expiretm:
            params['expiretm'] = expiretm

        # Close order (take-profit / stop-loss)
        if close_ordertype:
            params['close[ordertype]'] = close_ordertype
        if close_price is not None:
            params['close[price]'] = str(close_price)
        if close_price2 is not None:
            params['close[price2]'] = str(close_price2)

        # Validation mode
        if validate:
            params['validate'] = 'true'

        return self._query_private('AddOrder', params)

    def cancel_order(self, txid: str) -> Dict:
        """
        Annule un ordre

        Args:
            txid: ID de transaction de l'ordre

        Returns:
            Dict avec résultat de l'annulation
        """
        return self._query_private('CancelOrder', {'txid': txid})

    def get_account_balance(self) -> Dict:
        """
        Récupère le solde du compte

        Returns:
            Dict avec balances par asset
        """
        return self._query_private('Balance')

    def get_trade_history(
        self,
        type_: Optional[str] = None,
        trades: bool = False,
        start: Optional[int] = None,
        end: Optional[int] = None,
        ofs: Optional[int] = None
    ) -> Dict:
        """
        Récupère l'historique des trades

        Args:
            type_: Type de trade ('all', 'any position', 'closed position', etc.)
            trades: Inclure les trades liés aux positions
            start: Timestamp de début
            end: Timestamp de fin
            ofs: Offset de résultat

        Returns:
            Dict avec historique des trades
        """
        params = {}
        if type_:
            params['type'] = type_
        if trades:
            params['trades'] = 'true'
        if start:
            params['start'] = str(start)
        if end:
            params['end'] = str(end)
        if ofs:
            params['ofs'] = str(ofs)

        return self._query_private('TradesHistory', params)
