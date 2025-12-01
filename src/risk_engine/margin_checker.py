"""
Margin Checker Module
Vérifie les niveaux de marge et collateral via TradeBalance API
"""
import logging
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class MarginChecker:
    """
    Vérifie les niveaux de marge et s'assure que le compte a assez de collateral
    """

    def __init__(
        self,
        min_margin_level: float = 150.0,  # 150% minimum
        warning_margin_level: float = 200.0,  # 200% warning threshold
        min_free_margin_pct: float = 0.20  # 20% de free margin minimum
    ):
        """
        Initialise le MarginChecker

        Args:
            min_margin_level: Niveau de marge minimum en % (ex: 150 = 150%)
            warning_margin_level: Seuil d'avertissement
            min_free_margin_pct: % de free margin minimum requis
        """
        self.min_margin_level = min_margin_level
        self.warning_margin_level = warning_margin_level
        self.min_free_margin_pct = min_free_margin_pct

    def check_margin(self, trade_balance: Dict) -> Dict:
        """
        Vérifie le niveau de marge depuis TradeBalance API

        Args:
            trade_balance: Résultat de l'API TradeBalance avec:
                - eb: equivalent balance (balance + credit)
                - tb: trade balance (equity)
                - m: margin amount of open positions
                - n: unrealized net P&L of open positions
                - c: cost basis of open positions
                - v: current floating valuation of open positions
                - e: equity = tb + n
                - mf: free margin = e - m
                - ml: margin level = (e / m) * 100 si m > 0

        Returns:
            Dict avec:
            {
                'sufficient': bool,    # Marge suffisante
                'margin_level': float, # Niveau de marge en %
                'free_margin': float,  # Marge libre
                'used_margin': float,  # Marge utilisée
                'equity': float,       # Équité
                'warning': bool,       # Avertissement si proche du minimum
                'message': str         # Message explicatif
            }
        """
        try:
            # Extraire les valeurs (gérer le cas où l'API retourne des strings)
            equity = float(trade_balance.get('e', 0))  # Equity
            used_margin = float(trade_balance.get('m', 0))  # Margin used
            free_margin = float(trade_balance.get('mf', 0))  # Free margin

            # Margin level peut être fourni directement
            if 'ml' in trade_balance and trade_balance['ml']:
                margin_level = float(trade_balance['ml'])
            else:
                # Calculer margin level: (equity / used_margin) * 100
                if used_margin > 0:
                    margin_level = (equity / used_margin) * 100
                else:
                    # Pas de positions ouvertes = pas de margin utilisé
                    margin_level = float('inf')

            # Vérifier si la marge est suffisante
            sufficient = True
            warning = False
            message = "Niveau de marge OK"

            # Cas 1: Pas de positions = OK
            if used_margin == 0:
                sufficient = True
                message = "Aucune position ouverte - marge non applicable"

            # Cas 2: Margin level trop bas
            elif margin_level < self.min_margin_level:
                sufficient = False
                message = (
                    f"⛔ Niveau de marge insuffisant: {margin_level:.1f}% "
                    f"(min: {self.min_margin_level:.1f}%)"
                )

            # Cas 3: Margin level dans la zone d'avertissement
            elif margin_level < self.warning_margin_level:
                sufficient = True
                warning = True
                message = (
                    f"⚠️ Niveau de marge proche du minimum: {margin_level:.1f}% "
                    f"(warning: {self.warning_margin_level:.1f}%)"
                )

            # Cas 4: Free margin insuffisant
            free_margin_pct = (free_margin / equity) if equity > 0 else 0
            if free_margin_pct < self.min_free_margin_pct:
                if sufficient:  # Ne pas overwrite un échec précédent
                    warning = True
                    message += (
                        f" | Free margin faible: {free_margin_pct:.1%} "
                        f"(min: {self.min_free_margin_pct:.1%})"
                    )

            return {
                'sufficient': sufficient,
                'margin_level': round(margin_level, 2),
                'free_margin': round(free_margin, 2),
                'used_margin': round(used_margin, 2),
                'equity': round(equity, 2),
                'warning': warning,
                'message': message
            }

        except Exception as e:
            logger.error(f"Erreur lors de la vérification de la marge: {e}")
            return {
                'sufficient': False,
                'margin_level': 0.0,
                'free_margin': 0.0,
                'used_margin': 0.0,
                'equity': 0.0,
                'warning': False,
                'message': f"Erreur: {str(e)}"
            }

    def can_open_position(
        self,
        trade_balance: Dict,
        additional_margin_required: float
    ) -> Tuple[bool, str]:
        """
        Vérifie si on peut ouvrir une nouvelle position

        Args:
            trade_balance: Résultat de l'API TradeBalance
            additional_margin_required: Margin requis pour la nouvelle position

        Returns:
            Tuple (can_open, reason)
        """
        try:
            equity = float(trade_balance.get('e', 0))
            used_margin = float(trade_balance.get('m', 0))
            free_margin = float(trade_balance.get('mf', 0))

            # Vérifier si assez de free margin
            if additional_margin_required > free_margin:
                return False, (
                    f"Free margin insuffisant: {free_margin:.2f} "
                    f"< requis: {additional_margin_required:.2f}"
                )

            # Simuler le nouveau margin level
            new_used_margin = used_margin + additional_margin_required
            new_margin_level = (equity / new_used_margin) * 100 if new_used_margin > 0 else float('inf')

            # Vérifier que le nouveau margin level serait acceptable
            if new_margin_level < self.min_margin_level:
                return False, (
                    f"Nouveau margin level serait trop bas: {new_margin_level:.1f}% "
                    f"(min: {self.min_margin_level:.1f}%)"
                )

            # Vérifier le free margin après ouverture
            new_free_margin = equity - new_used_margin
            new_free_margin_pct = new_free_margin / equity if equity > 0 else 0

            if new_free_margin_pct < self.min_free_margin_pct:
                return False, (
                    f"Free margin restant serait insuffisant: {new_free_margin_pct:.1%} "
                    f"(min: {self.min_free_margin_pct:.1%})"
                )

            return True, "Marge suffisante pour nouvelle position"

        except Exception as e:
            logger.error(f"Erreur vérification ouverture position: {e}")
            return False, f"Erreur: {str(e)}"

    def parse_trade_balance_response(self, api_response: Dict) -> Optional[Dict]:
        """
        Parse et valide la réponse de l'API TradeBalance

        Args:
            api_response: Réponse complète de l'API (avec 'result' et 'error')

        Returns:
            Dict avec trade balance ou None si erreur
        """
        if not api_response:
            logger.error("Réponse API vide")
            return None

        if api_response.get('error'):
            errors = api_response['error']
            logger.error(f"Erreur API TradeBalance: {errors}")
            return None

        result = api_response.get('result')
        if not result:
            logger.error("Pas de 'result' dans la réponse API")
            return None

        # Valider que les champs essentiels sont présents
        required_fields = ['e', 'mf']  # equity et free margin minimum
        for field in required_fields:
            if field not in result:
                logger.warning(f"Champ '{field}' manquant dans TradeBalance")

        return result

    def get_margin_call_distance(self, trade_balance: Dict) -> Dict:
        """
        Calcule la distance jusqu'au margin call

        Args:
            trade_balance: Résultat de l'API TradeBalance

        Returns:
            Dict avec:
            {
                'distance_pct': float,     # Distance en % jusqu'au margin call
                'price_drop_allowed': float,  # % de baisse de prix toléré
                'safe': bool,              # True si distance confortable
                'message': str
            }
        """
        try:
            equity = float(trade_balance.get('e', 0))
            used_margin = float(trade_balance.get('m', 0))

            if used_margin == 0:
                return {
                    'distance_pct': float('inf'),
                    'price_drop_allowed': float('inf'),
                    'safe': True,
                    'message': "Aucune position ouverte"
                }

            current_margin_level = (equity / used_margin) * 100

            # Distance en % par rapport au minimum
            distance = current_margin_level - self.min_margin_level

            # Calculer la baisse de prix tolérée
            # Si margin level = 200% et min = 150%
            # On peut perdre (200-150)/200 = 25% de l'équité
            equity_loss_allowed = (distance / current_margin_level) if current_margin_level > 0 else 0

            safe = distance > 50  # Au moins 50% au-dessus du minimum

            if safe:
                message = f"Marge confortable: {distance:.1f}% au-dessus du minimum"
            else:
                message = f"⚠️ Marge serrée: {distance:.1f}% au-dessus du minimum"

            return {
                'distance_pct': round(distance, 2),
                'price_drop_allowed': round(equity_loss_allowed * 100, 2),
                'safe': safe,
                'message': message
            }

        except Exception as e:
            logger.error(f"Erreur calcul distance margin call: {e}")
            return {
                'distance_pct': 0.0,
                'price_drop_allowed': 0.0,
                'safe': False,
                'message': f"Erreur: {str(e)}"
            }
