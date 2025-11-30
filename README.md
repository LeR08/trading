# 🚀 Kraken Professional Margin Trading Bot

Un bot de trading professionnel pour Kraken avec **interface web moderne**, support du trading sur marge (leverage), analyse technique multi-indicateurs, et gestion automatique des risques.

## ✨ Nouvelle Interface Web!

🌐 **Dashboard en temps réel** avec Socket.IO pour monitoring et contrôle complet du bot!

![Dashboard Features](https://img.shields.io/badge/Dashboard-Real--time-00d4ff)
![Trading-Automated](https://img.shields.io/badge/Trading-Automated-00ff88)
![Leverage-3x](https://img.shields.io/badge/Leverage-3x-ffd700)

## ⚡ Fonctionnalités

### 🌐 Interface Web Moderne
- **Dashboard en temps réel** - Mises à jour live avec WebSocket
- **Configuration visuelle** - Configurer les clés API via l'interface
- **Graphiques et métriques** - Visualisation complète des indicateurs
- **Contrôle du bot** - Démarrer/Arrêter en un clic
- **Logs en direct** - Surveillance en temps réel
- **Design moderne** - Interface sombre et professionnelle
- **Responsive** - Fonctionne sur mobile et desktop

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

### 1. Aller dans le répertoire
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

## 🚀 Utilisation

### 🌐 Interface Web (RECOMMANDÉ)

**Démarrer l'interface web:**
```bash
./start_web.sh
# ou
python web_app.py
```

Puis ouvrez votre navigateur à:
- **Dashboard:** http://localhost:5000
- **Settings:** http://localhost:5000/settings

#### Configuration via l'interface web:
1. Allez sur http://localhost:5000/settings
2. Entrez vos clés API Kraken
3. Cliquez sur "Test Connection" pour vérifier
4. Sauvegardez la configuration
5. Retournez au Dashboard
6. Cliquez sur "Start Bot" pour démarrer!

### 💻 Mode Console (Alternative)

**Démarrer en mode console:**
```bash
python bot.py
```

**Configuration manuelle (.env):**
```bash
nano .env
```

Ajoutez vos clés:
```env
KRAKEN_API_KEY=votre_cle_api
KRAKEN_API_SECRET=votre_secret_api
```

## 🎨 Captures d'écran de l'Interface

### Dashboard Principal
- Prix BTC en temps réel
- Indicateurs techniques (RSI, MACD, EMA, etc.)
- Signal de trading actuel (BUY/SELL/HOLD)
- Balance du compte
- Positions ouvertes
- Logs en direct

### Page Settings
- Configuration des clés API
- Test de connexion
- Paramètres de trading (leverage, TP, SL)
- Gestion des risques

## ⚙️ Configuration

### Via l'Interface Web
Accédez à http://localhost:5000/settings pour configurer:

- **API Credentials** - Clés Kraken
- **Trading Pair** - XXBTZUSD (BTC/USD)
- **Leverage** - 1-5x (par défaut 3x)
- **Take Profit** - % de profit (par défaut 3%)
- **Stop Loss** - % de perte (par défaut 9%)
- **Check Interval** - Secondes entre analyses (par défaut 60s)
- **Position Limits** - Taille min/max des ordres

### Via Fichier .env
```env
KRAKEN_API_KEY=votre_cle_api
KRAKEN_API_SECRET=votre_secret_api

TRADING_PAIR=XXBTZUSD
LEVERAGE=3
TAKE_PROFIT_PERCENT=3.0
STOP_LOSS_PERCENT=9.0

CHECK_INTERVAL=60
MIN_ORDER_SIZE=0.001
MAX_POSITION_SIZE=0.1

MAX_DAILY_LOSS_PERCENT=15.0
MAX_OPEN_POSITIONS=1
```

## 📊 Fonctionnalités de l'Interface Web

### Dashboard en Temps Réel
- ✅ Mises à jour automatiques via WebSocket
- ✅ Prix BTC et données de marché live
- ✅ Indicateurs techniques en temps réel
- ✅ Signal de trading actuel avec force du signal
- ✅ Balance du compte actualisée
- ✅ Positions ouvertes avec P&L
- ✅ Historique des trades récents
- ✅ Logs en direct avec code couleur

### Contrôle du Bot
- ✅ Démarrer/Arrêter le bot en un clic
- ✅ Statut visible (Running/Stopped)
- ✅ Compteur d'itérations
- ✅ Rafraîchissement manuel des données

### Configuration Facile
- ✅ Formulaire pour les clés API
- ✅ Test de connexion avant sauvegarde
- ✅ Configuration complète du trading
- ✅ Aide et documentation intégrée

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
6. **L'interface web est en HTTP - utilisez uniquement en local**

### 📱 Monitoring
1. **Surveillez le bot régulièrement**
2. **Vérifiez les logs dans l'interface web**
3. **Consultez vos positions sur Kraken**
4. **Ayez un plan pour fermer les positions manuellement si nécessaire**

## 📁 Structure du Projet

```
trading/
├── web_app.py             # Application web Flask (NOUVEAU!)
├── bot.py                 # Bot en mode console
├── config.py              # Configuration
├── kraken_client.py       # Client API Kraken
├── strategy.py            # Stratégie de trading
├── indicators.py          # Indicateurs techniques
├── requirements.txt       # Dépendances Python
├── start_web.sh          # Script de démarrage web (NOUVEAU!)
├── start.sh              # Script de démarrage console
├── test_connection.py    # Test de connexion API
│
├── templates/            # Templates HTML (NOUVEAU!)
│   ├── dashboard.html    # Dashboard principal
│   └── settings.html     # Page de configuration
│
├── static/               # Fichiers statiques (NOUVEAU!)
│   ├── css/
│   │   └── style.css     # Styles modernes
│   └── js/
│       └── dashboard.js  # JavaScript temps réel
│
├── .env                  # Configuration secrète (NON COMMITÉ)
├── .env.example          # Exemple de configuration
├── .gitignore            # Fichiers ignorés
├── trading_bot.log       # Logs du bot
└── README.md             # Ce fichier
```

## 🔍 Logs et Monitoring

### Via l'Interface Web
Les logs s'affichent en temps réel dans le dashboard avec code couleur:
- 🔵 **Info** - Informations générales
- 🟢 **Success** - Opérations réussies
- 🟡 **Warning** - Avertissements
- 🔴 **Error** - Erreurs

### Via Fichier
Les logs sont aussi enregistrés dans `trading_bot.log`:
```bash
tail -f trading_bot.log
```

## 🛠️ Développement et Personnalisation

### Modifier les Indicateurs
Éditez `config.py` pour changer les périodes:
```python
RSI_PERIOD = 14
MACD_FAST = 12
MACD_SLOW = 26
EMA_SHORT = 9
EMA_MEDIUM = 21
EMA_LONG = 50
```

### Ajuster la Stratégie
Éditez `indicators.py` dans `get_trading_signals()` pour modifier:
- Les poids des indicateurs
- Le seuil de signal (60%)
- Les conditions de trading

### Personnaliser l'Interface
- **CSS:** `/static/css/style.css`
- **JavaScript:** `/static/js/dashboard.js`
- **Templates:** `/templates/*.html`

## 📞 Support et Questions

### Ressources Kraken
- [Documentation API](https://docs.kraken.com/rest/)
- [Support Kraken](https://support.kraken.com/)

### Technologies Utilisées
- **Backend:** Flask, Socket.IO, Eventlet
- **Frontend:** HTML5, CSS3, JavaScript (ES6+)
- **Graphiques:** Chart.js
- **UI:** Bootstrap 5, Font Awesome
- **Trading:** krakenex, ta (Technical Analysis)

## 🎯 Démarrage Rapide

### Option 1: Interface Web (Recommandé)
```bash
cd /home/user/trading
./start_web.sh
# Ouvrez http://localhost:5000 dans votre navigateur
# Configurez vos clés API dans Settings
# Démarrez le bot depuis le Dashboard!
```

### Option 2: Mode Console
```bash
cd /home/user/trading
nano .env  # Ajoutez vos clés API
./start.sh
```

## 📝 Changelog

### Version 2.0 (Interface Web)
- ✅ Interface web complète avec dashboard temps réel
- ✅ Configuration des clés API via l'interface
- ✅ Graphiques et métriques en temps réel
- ✅ Contrôle du bot (start/stop) via web
- ✅ Logs en direct avec WebSocket
- ✅ Design moderne et responsive

### Version 1.0 (Console)
- ✅ Bot de trading en ligne de commande
- ✅ Multi-indicateurs techniques
- ✅ Trading sur marge avec TP/SL
- ✅ Gestion des risques

## 📜 Licence

Ce projet est fourni "tel quel" sans garantie. Utilisez-le à vos propres risques.

---

**Bon trading! 🚀📈**

**Rappel**:
- 🌐 Utilisez l'interface web pour une meilleure expérience!
- 🔐 Ne partagez jamais vos clés API
- ⚠️ Ne tradez que ce que vous pouvez vous permettre de perdre
- 📊 Surveillez régulièrement vos positions
