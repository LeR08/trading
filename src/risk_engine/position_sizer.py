"""
Position Sizer Module
Calcule la taille optimale des positions selon le risque et le levier
"""
import logging
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class PositionSizer:
    """
    Calcule la taille des positions en tenant compte du risque et du levier
    """

    def __init__(
        self,
        default_risk_pct: float = 0.03,
        max_exposure_pct: float = 0.10,
        default_leverage: int = 3
    ):
        """
        Initialise le PositionSizer

        Args:
            default_risk_pct: Risque par trade (ex: 0.03 = 3%)
            max_exposure_pct: Exposition maximale totale (ex: 0.10 = 10%)
            default_leverage: Levier par défaut
        """
        self.default_risk_pct = default_risk_pct
        self.max_exposure_pct = max_exposure_pct
        self.default_leverage = default_leverage

    def calc_size(
        self,
        equity: float,
        price: float,
        risk_pct: Optional[float] = None,
        leverage: Optional[int] = None,
        stop_loss_pct: Optional[float] = None,
        asset_pair_info: Optional[Dict] = None
    ) -> Dict:
        """
        Calcule la taille de position et margin requis

        Args:
            equity: Capital disponible (en quote currency, ex: EUR/USD)
            price: Prix actuel de l'asset (BTC)
            risk_pct: Risque par trade (optionnel, sinon utilise default)
            leverage: Levier à utiliser (optionnel, sinon utilise default)
            stop_loss_pct: Distance stop loss en % (ex: 0.03 = 3%)
            asset_pair_info: Info depuis AssetPairs API (pour valider min/max)

        Returns:
            Dict avec:
            {
                'volume': float,          # Volume en BTC
                'margin_required': float, # Margin requis
                'position_value': float,  # Valeur totale de la position
                'leverage': int,          # Levier utilisé
                'risk_amount': float,     # Montant risqué
                'valid': bool,            # Position valide selon contraintes
                'reason': str             # Raison si invalide
            }
        """
        risk = risk_pct or self.default_risk_pct
        lev = leverage or self.default_leverage

        # Validation des inputs
        if equity <= 0:
            return self._invalid_result("Équité insuffisante ou négative")

        if price <= 0:
            return self._invalid_result("Prix invalide")

        # Montant du risque en valeur absolue
        risk_amount = equity * risk

        # Si stop_loss_pct fourni, calculer position_size en fonction
        if stop_loss_pct and stop_loss_pct > 0:
            # Position size = risk_amount / (stop_loss_pct * price)
            # Avec leverage: on peut avoir une position plus grande
            position_value_base = risk_amount / stop_loss_pct
            position_value = position_value_base * lev
        else:
            # Sinon, utiliser le risque directement
            position_value = risk_amount * lev

        # Volume en BTC
        volume = position_value / price

        # Margin requis (sans leverage, ce serait position_value, avec leverage c'est divisé)
        margin_required = position_value / lev

        # Vérifier que margin requis ne dépasse pas l'équité
        if margin_required > equity:
            return self._invalid_result(
                f"Margin requis ({margin_required:.2f}) > équité ({equity:.2f})"
            )

        # Vérifier exposition maximale
        exposure_pct = position_value / equity
        if exposure_pct > self.max_exposure_pct * lev:
            return self._invalid_result(
                f"Exposition ({exposure_pct:.2%}) dépasse le max "
                f"({self.max_exposure_pct * lev:.2%})"
            )

        # Valider selon AssetPairs si fourni
        if asset_pair_info:
            validation_ok, validation_msg = self._validate_asset_pair_constraints(
                volume,
                asset_pair_info
            )
            if not validation_ok:
                return self._invalid_result(validation_msg)

        return {
            'volume': round(volume, 8),
            'margin_required': round(margin_required, 2),
            'position_value': round(position_value, 2),
            'leverage': lev,
            'risk_amount': round(risk_amount, 2),
            'valid': True,
            'reason': 'Position valide'
        }

    def _validate_asset_pair_constraints(
        self,
        volume: float,
        asset_pair_info: Dict
    ) -> Tuple[bool, str]:
        """
        Valide les contraintes selon AssetPairs (min/max qty, decimals, etc.)

        Args:
            volume: Volume calculé
            asset_pair_info: Info depuis Kraken AssetPairs API

        Returns:
            Tuple (is_valid, message)
        """
        # IMPORTANT: Ici on devrait valider selon les infos de AssetPairs
        # Exemple de champs à vérifier:
        # - ordermin: taille minimale d'ordre
        # - lot_decimals: précision du volume
        # - pair_decimals: précision du prix
        # - costmin: coût minimum

        try:
            # Exemple de validation (à adapter selon la structure réelle)
            ordermin = float(asset_pair_info.get('ordermin', 0))
            lot_decimals = int(asset_pair_info.get('lot_decimals', 8))

            if volume < ordermin:
                return False, f"Volume {volume} < minimum {ordermin}"

            # Vérifier la précision
            # (Le volume doit être arrondi selon lot_decimals)
            volume_rounded = round(volume, lot_decimals)
            if abs(volume - volume_rounded) > 1e-10:
                logger.warning(
                    f"Volume ajusté de {volume} à {volume_rounded} "
                    f"selon lot_decimals={lot_decimals}"
                )

            return True, "Validation OK"

        except Exception as e:
            logger.error(f"Erreur validation asset pair: {e}")
            return False, f"Erreur validation: {str(e)}"

    def _invalid_result(self, reason: str) -> Dict:
        """
        Retourne un résultat invalide

        Args:
            reason: Raison de l'invalidité

        Returns:
            Dict avec valid=False
        """
        return {
            'volume': 0.0,
            'margin_required': 0.0,
            'position_value': 0.0,
            'leverage': 0,
            'risk_amount': 0.0,
            'valid': False,
            'reason': reason
        }

    def calculate_total_exposure(
        self,
        open_positions: list,
        equity: float
    ) -> float:
        """
        Calcule l'exposition totale actuelle

        Args:
            open_positions: Liste des positions ouvertes avec leur valeur
            equity: Équité actuelle

        Returns:
            Exposition totale en pourcentage de l'équité
        """
        if equity <= 0:
            return 0.0

        total_position_value = sum(
            pos.get('position_value', 0) for pos in open_positions
        )

        exposure = total_position_value / equity

        return exposure

    def can_open_new_position(
        self,
        open_positions: list,
        equity: float,
        new_position_value: float
    ) -> Tuple[bool, str]:
        """
        Vérifie si on peut ouvrir une nouvelle position

        Args:
            open_positions: Positions ouvertes actuelles
            equity: Équité actuelle
            new_position_value: Valeur de la nouvelle position

        Returns:
            Tuple (can_open, reason)
        """
        current_exposure = self.calculate_total_exposure(open_positions, equity)
        new_exposure = (new_position_value / equity) if equity > 0 else float('inf')
        total_exposure = current_exposure + new_exposure

        max_allowed = self.max_exposure_pct * self.default_leverage

        if total_exposure > max_allowed:
            return False, (
                f"Exposition totale ({total_exposure:.2%}) dépasserait "
                f"le maximum ({max_allowed:.2%})"
            )

        return True, "OK"
