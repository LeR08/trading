# =€ Bot de Trading Professionnel Kraken - Multi-Timeframe

Bot de trading professionnel avec analyse multi-timeframe complète et envoi de signaux via webhook.

## <¯ Features

-  **Analyse Multi-Timeframe**: Analyse toutes les timeframes Kraken (1m, 5m, 15m, 30m, 1h, 4h, 1D, 1W, 15D)
-  **Score de Confiance Pondéré**: Calcul intelligent basé sur la convergence des signaux
-  **Webhook Integration**: Envoi automatique des signaux de trading
-  **Marge x10**: Trading avec leverage maximal
-  **TP/SL Automatiques**: Take Profit et Stop Loss configurables
-  **Trading Réel**: Pas de simulation, trading en direct
-  **Gestion de Risque**: Limites de pertes journalières et sizing automatique

## =Ê Timeframes Analysées

Le bot analyse toutes les timeframes disponibles sur l'API Kraken:

| Timeframe | Minutes | Description |
|-----------|---------|-------------|
| 1m | 1 | 1 minute |
| 5m | 5 | 5 minutes |
| 15m | 15 | 15 minutes |
| 30m | 30 | 30 minutes |
| 1h | 60 | 1 heure |
| 4h | 240 | 4 heures |
| 1D | 1440 | 1 jour |
| 1W | 10080 | 1 semaine |
| 15D | 21600 | 15 jours |

## =' Installation

### 1. Prérequis

```bash
pip install krakenex pandas numpy requests python-dotenv
```

### 2. Configuration

Créez un fichier `.env` à partir de `.env.example`:

```bash
cp .env.example .env
```

Éditez le fichier `.env` avec vos paramètres:

```bash
# API Kraken
KRAKEN_API_KEY=votre_cle_api
KRAKEN_API_SECRET=votre_secret_api

# Webhook
WEBHOOK_URL=https://votre-webhook.com/trading-signals

# Trading Parameters
LEVERAGE=10
TAKE_PROFIT_PERCENT=5.0
STOP_LOSS_PERCENT=2.0

# Timeframes (séparer par des virgules)
TIMEFRAMES=5,15,60,240,1440

# Score de confiance minimum pour trader
MIN_CONFIDENCE_SCORE=70
```

## =€ Utilisation

### Lancer le bot

```bash
python3 pro_trading_bot.py
```

Le bot va:
1.  Tester la connexion à Kraken API
2.  Tester la connexion au webhook
3. = Analyser toutes les timeframes configurées
4. =Ê Calculer le score de confiance
5. =ä Envoyer les signaux via webhook si conditions remplies

### Mode d'exécution automatique (optionnel)

Par défaut, le bot **envoie seulement les signaux via webhook** sans exécuter de trades.

Pour activer l'exécution automatique des trades, décommentez la ligne dans `pro_trading_bot.py`:

```python
# Ligne 167 (environ)
self.execute_trade(signal_data)  # Décommenter cette ligne
```

  **ATTENTION**: L'exécution automatique place des ordres réels avec de l'argent réel!

## =ä Format du Webhook

Le bot envoie un payload JSON complet via webhook:

```json
{
  "timestamp": "2025-12-03T20:30:00",
  "bot_version": "2.0-professional",
  "signal_type": "MULTI_TIMEFRAME_ANALYSIS",

  "signal": {
    "action": "BUY",
    "pair": "BTC/USD",
    "leverage": 10,
    "confidence_score": 85,
    "position_size": 0.05
  },

  "prices": {
    "entry": 45000.00,
    "take_profit": 47250.00,
    "stop_loss": 44100.00,
    "current_price": 45000.00
  },

  "targets": {
    "tp_percent": 5.0,
    "sl_percent": 2.0,
    "tp_distance_usd": 2250.00,
    "sl_distance_usd": 900.00,
    "risk_reward_ratio": 2.5
  },

  "timeframe_analysis": {
    "overall_signal": "BUY",
    "convergence": true,
    "convergence_ratio": 85.5,
    "bullish_weight": 25.5,
    "bearish_weight": 5.2,
    "total_weight": 30.0,
    "best_timeframes": [
      {"timeframe": "1D", "strength": 85.5, "weight": 7},
      {"timeframe": "4h", "strength": 82.3, "weight": 6},
      {"timeframe": "1h", "strength": 78.9, "weight": 5}
    ]
  },

  "analysis": {
    "reason": "Tendance haussière avec forte convergence (85%). Signaux forts sur: 1D, 4h, 1h.",
    "indicators": {
      "rsi": 65.5,
      "macd": 125.5,
      "ema_short": 44800,
      "ema_medium": 44500,
      "ema_long": 44000
    }
  },

  "recommendation": {
    "type": "MARGIN_TRADE",
    "urgency": "HIGH",
    "risk_level": "MEDIUM"
  }
}
```

## =Ê Indicateurs Utilisés

Le bot utilise les indicateurs suivants pour chaque timeframe:

- **RSI** (Relative Strength Index)
- **MACD** (Moving Average Convergence Divergence)
- **EMA** (Exponential Moving Averages) - 9, 21, 50
- **Bollinger Bands**
- **Stochastic Oscillator**
- **Volume Analysis**
- **ATR** (Average True Range)

## <¯ Score de Confiance

Le score de confiance est calculé en fonction de:

1. **Convergence des timeframes**: Plus de timeframes dans la même direction = score plus élevé
2. **Poids des timeframes**: Les timeframes plus longues (1D, 1W) ont plus de poids
3. **Force des signaux**: Intensité de chaque signal individuel

### Niveaux de confiance:

- **90-100%**: Signal IMMÉDIAT - Très forte convergence
- **80-89%**: Signal FORT - Bonne convergence
- **70-79%**: Signal MOYEN - Convergence acceptable
- **<70%**: Pas de trade - Signaux mixtes

## ™ Configuration Avancée

### Poids des Timeframes

Vous pouvez ajuster le poids de chaque timeframe dans `.env`:

```bash
TIMEFRAME_WEIGHTS=1:1,5:2,15:3,30:4,60:5,240:6,1440:7,10080:5,21600:3
```

Format: `timeframe:poids`

### Gestion du Risque

```bash
# Risque maximum par trade: 2% du capital
# Position size calculée automatiquement

# Perte maximale journalière
MAX_DAILY_LOSS_PERCENT=10.0

# Nombre maximum de positions simultanées
MAX_OPEN_POSITIONS=3
```

## =Ý Logs

Le bot crée deux types de logs:

1. **Console**: Affichage en temps réel
2. **Fichier**: `pro_trading_bot.log` - Historique complet

## =á Sécurité

  **IMPORTANT**:

- Ne partagez JAMAIS vos clés API
- Gardez le fichier `.env` privé
- Utilisez des clés API avec permissions limitées
- Testez d'abord avec des petits montants
- Surveillez le bot régulièrement

## = Workflow

```
1. Bot démarre
   “
2. Connexions testées (Kraken + Webhook)
   “
3. Analyse multi-timeframe lancée
   “
4. Calcul du score de confiance
   “
5. Score >= MIN_CONFIDENCE_SCORE?
   “
   OUI ’ Envoi signal webhook
   “
   (Optionnel) Exécution automatique du trade
   “
6. Attente CHECK_INTERVAL secondes
   “
7. Retour à l'étape 3
```

## <“ Exemple de Session

```bash
$ python3 pro_trading_bot.py

TPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPW
Q        =€ BOT DE TRADING PROFESSIONNEL KRAKEN MULTI-TF =€         Q
ZPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPP]

™  CONFIGURATION
Paire: XXBTZUSD
Levier: 10x
Take Profit: 5.0%
Stop Loss: 2.0%
Score de confiance minimum: 70%

>ê Test des connexions...
    Kraken API OK - Prix BTC: $45,234.50
    Webhook OK

= ANALYSE MULTI-TIMEFRAME EN COURS
======================================================================

=È Analyse 1D (poids: 7)...
   Signal: BUY
   Force: 85.5%

=È Analyse 4h (poids: 6)...
   Signal: BUY
   Force: 82.3%

=È Analyse 1h (poids: 5)...
   Signal: BUY
   Force: 78.9%

======================================================================
=Ê RÉSULTAT DE L'ANALYSE MULTI-TIMEFRAME
======================================================================
Signal Global: BUY
Score de Confiance: 85%
Convergence:  OUI (85.5%)
Raison: Tendance haussière avec forte convergence (85%). Signaux forts sur: 1D, 4h, 1h.
======================================================================

( SIGNAL DE TRADING DÉTECTÉ!

=ä ENVOI DU SIGNAL VIA WEBHOOK
 Signal envoyé avec succès!

=Ë DÉTAILS DU SIGNAL ENVOYÉ:
   Action: BUY
   Paire: BTC/USD
   Levier: 10x
   Taille: 0.05 BTC
   Entry: $45,234.50
   TP: $47,496.23 (+5.0%)
   SL: $44,329.61 (-2.0%)
   Confiance: 85%
```

## <˜ Support

En cas de problème:

1. Vérifiez vos clés API Kraken
2. Vérifiez l'URL de votre webhook
3. Consultez les logs: `pro_trading_bot.log`
4. Vérifiez votre connexion internet

## =Ü License

Usage personnel uniquement. Trading à vos propres risques.

##   Disclaimer

**Ce bot exécute des trades réels avec de l'argent réel.**

- Les marchés crypto sont volatils
- Risque de perte totale du capital
- Pas de garantie de profits
- Utilisez à vos propres risques
- Testez d'abord avec de petits montants

**Le créateur du bot n'est pas responsable des pertes financières.**

---

Made with d for professional traders
