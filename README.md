# 🚀 Kraken Professional Margin Trading Bot

Un bot de trading professionnel pour Kraken avec support du trading sur marge (leverage), analyse technique multi-indicateurs, et gestion automatique des risques.

## ⚡ Fonctionnalités

### 📊 Analyse Technique Avancée
- **RSI (Relative Strength Index)** - Détection surachat/survente
- **MACD (Moving Average Convergence Divergence)** - Croisements de tendance
- **EMA (Exponential Moving Average)** - Moyennes mobiles 9/21/50
- **Bollinger Bands** - Bandes de volatilité
- **Stochastic Oscillator** - Momentum du marché
- **Volume Analysis** - Confirmation par le volume
- **ATR (Average True Range)** - Mesure de volatilité
- **Support/Resistance** - Niveaux clés

### 💰 Trading sur Marge
- **Leverage 3x** - Effet de levier configurable
- **Take Profit automatique** - TP à +3%
- **Stop Loss automatique** - SL à -9%
- **Trading BTC/USD uniquement**

### 🛡️ Gestion des Risques
- **Position sizing intelligent** - Calcul basé sur le risque (2% par trade)
- **Limite de perte journalière** - Protection à 15% de perte max/jour
- **Limite de positions ouvertes** - 1 position max simultanée
- **Validation des ordres** - Vérification avant exécution

### 📈 Système de Décision
Le bot analyse 7 indicateurs avec des poids différents :
- MACD (20%) - Signal de tendance
- EMA Trend (20%) - Alignement des moyennes
- RSI (15%) - Surachat/Survente
- Bollinger Bands (15%) - Volatilité
- Stochastic (10%) - Momentum
- Volume (10%) - Confirmation
- Support/Resistance (10%) - Niveaux clés

**Seuil de trading : 60%** - Le bot ne trade que si la force du signal dépasse 60%

## 📋 Prérequis

- Python 3.8+
- Compte Kraken avec API activée
- Permissions API : Query Funds, Create & Modify Orders, Query Open Orders & Trades
- **Marge activée** sur votre compte Kraken

## 🔧 Installation

### 1. Cloner le projet
```bash
cd /home/user/trading
```

### 2. Créer un environnement virtuel (recommandé)
```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows
```

### 3. Installer les dépendances
```bash
pip install -r requirements.txt
```

### 4. Configurer les clés API

**⚠️ IMPORTANT SÉCURITÉ:**
1. Connectez-vous à votre compte Kraken
2. Allez dans Settings → API
3. **RÉVOQUEZ** la clé que vous avez partagée publiquement
4. Créez une **NOUVELLE** clé API avec les permissions:
   - Query Funds
   - Create & Modify Orders
   - Query Open Orders & Trades
   - Query Closed Orders & Trades

5. Éditez le fichier `.env`:
```bash
nano .env  # ou utilisez votre éditeur préféré
```

6. Ajoutez vos nouvelles clés:
```env
KRAKEN_API_KEY=votre_nouvelle_cle_api
KRAKEN_API_SECRET=votre_secret_api
```

## 🚀 Utilisation

### Démarrer le bot
```bash
python bot.py
```

### Mode Test (Recommandé)
Avant de trader en réel, testez avec de petits montants:
1. Modifiez `.env`:
```env
MIN_ORDER_SIZE=0.001  # Montant minimum
MAX_POSITION_SIZE=0.01  # Limitez vos positions
```

2. Surveillez les premiers trades attentivement

### Arrêter le bot
Utilisez `Ctrl+C` pour arrêter le bot proprement. Il affichera un résumé des trades.

## ⚙️ Configuration

Éditez le fichier `.env` pour personnaliser:

```env
# Paire de trading
TRADING_PAIR=XXBTZUSD

# Effet de levier (1-5)
LEVERAGE=3

# Take Profit en % (par défaut 3%)
TAKE_PROFIT_PERCENT=3.0

# Stop Loss en % (par défaut 9%)
STOP_LOSS_PERCENT=9.0

# Intervalle de vérification en secondes (par défaut 60)
CHECK_INTERVAL=60

# Taille minimum d'ordre (BTC)
MIN_ORDER_SIZE=0.001

# Taille maximum de position (BTC)
MAX_POSITION_SIZE=0.1

# Limite de perte journalière (%)
MAX_DAILY_LOSS_PERCENT=15.0

# Nombre max de positions ouvertes
MAX_OPEN_POSITIONS=1
```

## 📊 Exemple de Sortie

```
╔════════════════════════════════════════════════════════════════╗
║                                                                ║
║          🚀 KRAKEN PROFESSIONAL MARGIN TRADING BOT 🚀          ║
║                                                                ║
║  ⚡ Multi-Indicator Strategy                                   ║
║  📊 Technical Analysis: RSI, MACD, EMA, BB, Stochastic         ║
║  💰 3x Leverage Margin Trading                                 ║
║  🎯 Auto TP/SL: +3% / -9%                                      ║
║  🛡️ Advanced Risk Management                                   ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝

======================================================================
🕐 2025-11-30 21:52:30 | Iteration #1
======================================================================

📈 Market Data (BTC/USD):
   Current Price: $97,234.50
   24h High: $98,150.00
   24h Low: $95,800.00
   24h Volume: 1,234.56 BTC

💼 Account Balance:
   USD: $10,000.00
   BTC: 0.000000 ($0.00)

📊 Open Positions: 0

🎯 Trading Signal:
   Signal: BUY
   Strength: 72.5%
   Reason: RSI oversold (28.5), MACD bullish crossover, Strong uptrend

📊 Key Indicators:
   RSI: 28.5 | MACD: 125.34 | Stoch: 18.2
   EMA(9): $96,850 | EMA(21): $95,920 | EMA(50): $94,100
   BB Upper: $99,200 | BB Lower: $94,800
   Volume Ratio: 1.85x | ATR: $1,234.50
```

## ⚠️ AVERTISSEMENTS IMPORTANTS

### 🚨 Risques du Trading
1. **Le trading comporte des risques élevés de perte**
2. **Le leverage augmente les gains ET les pertes**
3. **Ne tradez que ce que vous pouvez vous permettre de perdre**
4. **Les performances passées ne garantissent pas les résultats futurs**

### 🔐 Sécurité
1. **Ne partagez JAMAIS vos clés API**
2. **Le fichier `.env` est dans `.gitignore` - ne le commitez JAMAIS**
3. **Utilisez des clés API avec permissions limitées**
4. **Révocez et recréez vos clés régulièrement**
5. **Activez 2FA sur votre compte Kraken**

### 📱 Monitoring
1. **Surveillez le bot régulièrement**
2. **Vérifiez les logs dans `trading_bot.log`**
3. **Consultez vos positions sur Kraken**
4. **Ayez un plan pour fermer les positions manuellement si nécessaire**

## 📁 Structure du Projet

```
trading/
├── bot.py                 # Bot principal
├── config.py              # Configuration
├── kraken_client.py       # Client API Kraken
├── strategy.py            # Stratégie de trading
├── indicators.py          # Indicateurs techniques
├── requirements.txt       # Dépendances Python
├── .env                   # Configuration secrète (NON COMMITÉ)
├── .env.example          # Exemple de configuration
├── .gitignore            # Fichiers ignorés par Git
├── trading_bot.log       # Logs du bot
└── README.md             # Ce fichier
```

## 🔍 Logs et Monitoring

Les logs sont enregistrés dans `trading_bot.log` et affichés dans la console.

Pour suivre les logs en temps réel:
```bash
tail -f trading_bot.log
```

## 🛠️ Développement et Personnalisation

### Modifier les Indicateurs
Éditez `config.py` pour changer les périodes des indicateurs:
```python
RSI_PERIOD = 14
MACD_FAST = 12
MACD_SLOW = 26
EMA_SHORT = 9
EMA_MEDIUM = 21
EMA_LONG = 50
```

### Ajuster la Stratégie
Éditez `indicators.py` dans la fonction `get_trading_signals()` pour modifier:
- Les poids des indicateurs
- Le seuil de signal (actuellement 60%)
- Les conditions de trading

## 📞 Support et Questions

- Documentation Kraken API: https://docs.kraken.com/rest/
- Documentation TA Library: https://technical-analysis-library-in-python.readthedocs.io/

## 📜 Licence

Ce projet est fourni "tel quel" sans garantie. Utilisez-le à vos propres risques.

## 🎯 Prochaines Étapes

1. ✅ Installer les dépendances
2. ✅ Configurer les clés API (nouvelles clés!)
3. ⚠️ Tester avec de petits montants
4. 📊 Surveiller les premiers trades
5. ⚙️ Ajuster la configuration selon vos besoins
6. 🚀 Lancer en production (avec prudence!)

---

**Bon trading! 🚀📈**

**Rappel**: Ne tradez que ce que vous pouvez vous permettre de perdre.
