# Guide Opérateur - Kraken BTC Trading Bot

Guide complet pour déployer et opérer le bot de trading Kraken BTC avec marge x3.

## 📋 Table des Matières

1. [Architecture](#architecture)
2. [Prérequis](#prérequis)
3. [Installation](#installation)
4. [Configuration](#configuration)
5. [Déploiement](#déploiement)
6. [Monitoring](#monitoring)
7. [Opérations](#opérations)
8. [Troubleshooting](#troubleshooting)
9. [Sécurité](#sécurité)

---

## 🏗️ Architecture

### Composants Principaux

```
┌──────────────────────────────────────────┐
│           Trading Bot                    │
│                                          │
│  ┌────────────┐  ┌────────────────┐    │
│  │ Strategies │→→│  Risk Engine   │    │
│  └────────────┘  └────────────────┘    │
│         ↓               ↓               │
│  ┌────────────────────────────┐        │
│  │    Order Executor          │        │
│  └────────────────────────────┘        │
│         ↓                               │
│  ┌────────────────────────────┐        │
│  │    Kraken API Client       │        │
│  └────────────────────────────┘        │
│         ↓                               │
└─────────┼───────────────────────────────┘
          ↓
   ┌─────────────┐
   │ Kraken API  │
   └─────────────┘
```

### Modules

- **strategies/**: 3 stratégies de trading (trend_following, mean_reversion, breakout)
- **risk_engine/**: Gestion des risques (position sizing, circuit breaker, margin checker)
- **executor/**: Exécution d'ordres avec retry logic
- **backtest/**: Moteur de backtesting
- **monitoring/**: Métriques Prometheus
- **api/**: Client API Kraken

---

## 🔧 Prérequis

### Compte Kraken

1. Compte Kraken vérifié avec KYC
2. **Marge activée** sur le compte
3. Clés API créées avec permissions :
   - Query Funds
   - Create & Modify Orders
   - Query Open Orders & Trades
   - Query Closed Orders & Trades

### Infrastructure

- **Docker** 20.10+
- **Kubernetes** 1.24+ (pour déploiement K8s)
- **Python** 3.11+ (pour développement local)
- **Prometheus** (pour monitoring)

### Ressources Minimales

- CPU: 0.5 core
- RAM: 512 MB
- Disk: 1 GB

---

## 📦 Installation

### 1. Clone du Repository

```bash
git clone <repository>
cd trading
```

### 2. Installation Locale (Développement)

```bash
# Créer environnement virtuel
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# Installer dépendances
pip install -r requirements_bot.txt
```

### 3. Build Docker Image

```bash
docker build -t kraken-trading-bot:latest .
```

---

## ⚙️ Configuration

### Variables d'Environnement

Créer un fichier `.env` basé sur `.env.example`:

```bash
# API Kraken (REQUIS)
KRK_KEY=your_api_key_here
KRK_SECRET=your_api_secret_here

# Configuration Trading
PAIR=XBTEUR                 # Paire de trading (BTC/EUR)
LEVERAGE=3                  # Effet de levier (1-5)
RISK_PER_TRADE=0.03        # 3% risque par trade
MAX_TOTAL_EXPOSURE=0.10    # 10% exposition max
SLIPPAGE_PCT=0.2           # 0.2% slippage estimé

# Risk Management
MAX_DRAWDOWN=0.15          # 15% drawdown max
MAX_DAILY_LOSS_PCT=0.05    # 5% perte journalière max
MAX_CONSECUTIVE_LOSSES=5    # 5 pertes consécutives max

# Stratégie
STRATEGY=trend_following    # trend_following | mean_reversion | breakout

# Execution
MAX_RETRIES=5              # Nombre max de retries
INTERVAL_SECONDS=300       # 5 minutes entre cycles

# Mode
DRY_RUN=true              # true = simulation, false = production

# Logging
LOG_LEVEL=INFO            # DEBUG | INFO | WARNING | ERROR
```

⚠️ **IMPORTANT**: Ne JAMAIS commit le fichier `.env` dans git!

### Paramètres Recommandés

#### Mode Conservateur
```bash
LEVERAGE=2
RISK_PER_TRADE=0.02
MAX_TOTAL_EXPOSURE=0.05
MAX_DRAWDOWN=0.10
```

#### Mode Agressif
```bash
LEVERAGE=3
RISK_PER_TRADE=0.03
MAX_TOTAL_EXPOSURE=0.15
MAX_DRAWDOWN=0.20
```

---

## 🚀 Déploiement

### Déploiement Local (Test)

```bash
# Mode dry-run
DRY_RUN=true python example_run.py

# Mode production (⚠️ ATTENTION)
DRY_RUN=false python example_run.py
```

### Déploiement Docker

```bash
# Dry-run
docker run -d \
  --name trading-bot \
  -e KRK_KEY="your_key" \
  -e KRK_SECRET="your_secret" \
  -e DRY_RUN=true \
  -p 9090:9090 \
  kraken-trading-bot:latest

# Vérifier logs
docker logs -f trading-bot
```

### Déploiement Kubernetes

1. **Créer le namespace:**
```bash
kubectl create namespace trading-bot
```

2. **Créer les secrets:**
```bash
kubectl create secret generic kraken-api-keys \
  --from-literal=api-key='YOUR_API_KEY' \
  --from-literal=api-secret='YOUR_API_SECRET' \
  -n trading-bot
```

3. **Déployer:**
```bash
kubectl apply -f k8s/deployment.yaml
```

4. **Vérifier:**
```bash
kubectl get pods -n trading-bot
kubectl logs -f deployment/kraken-trading-bot -n trading-bot
```

---

## 📊 Monitoring

### Métriques Prometheus

Le bot expose des métriques sur `http://localhost:9090/metrics`

#### Métriques Clés

| Métrique | Description |
|----------|-------------|
| `trading_equity` | Équité actuelle du compte |
| `trading_open_positions_total` | Nombre de positions ouvertes |
| `trading_margin_level_percent` | Niveau de marge (%) |
| `trading_unrealized_pnl` | P&L non réalisé |
| `trading_circuit_breaker_state` | État du circuit breaker |
| `trading_total_trades` | Nombre total de trades |
| `trading_orders_placed_total{status}` | Ordres placés par statut |

#### Queries Prometheus Utiles

```promql
# Win rate
rate(trading_winning_trades[1h]) / rate(trading_total_trades[1h])

# P&L par heure
rate(trading_realized_pnl[1h])

# Taux d'échec ordres
rate(trading_orders_placed_total{status="failed"}[5m])
```

### Dashboards Grafana

Importer le dashboard depuis `grafana/dashboard.json` (à créer si besoin)

### Alertes Recommandées

```yaml
# Margin Level Bas
- alert: LowMarginLevel
  expr: trading_margin_level_percent < 180
  for: 5m
  annotations:
    summary: "Margin level critique: {{ $value }}%"

# Circuit Breaker Ouvert
- alert: CircuitBreakerOpen
  expr: trading_circuit_breaker_state == 1
  for: 1m
  annotations:
    summary: "Circuit breaker déclenché"

# Drawdown Élevé
- alert: HighDrawdown
  expr: trading_drawdown_percent > 12
  for: 10m
  annotations:
    summary: "Drawdown élevé: {{ $value }}%"
```

---

## 🔄 Opérations

### Démarrage

```bash
# Local
python example_run.py

# Docker
docker start trading-bot

# Kubernetes
kubectl scale deployment kraken-trading-bot --replicas=1 -n trading-bot
```

### Arrêt

```bash
# Local
Ctrl+C

# Docker
docker stop trading-bot

# Kubernetes
kubectl scale deployment kraken-trading-bot --replicas=0 -n trading-bot
```

### Rotation des Clés API

1. Créer nouvelles clés sur Kraken
2. Mettre à jour le secret K8s:
```bash
kubectl delete secret kraken-api-keys -n trading-bot
kubectl create secret generic kraken-api-keys \
  --from-literal=api-key='NEW_KEY' \
  --from-literal=api-secret='NEW_SECRET' \
  -n trading-bot
```
3. Redémarrer le pod:
```bash
kubectl rollout restart deployment/kraken-trading-bot -n trading-bot
```

### Changement de Stratégie

```bash
# Modifier ConfigMap
kubectl edit configmap bot-config -n trading-bot

# Changer STRATEGY=mean_reversion

# Redémarrer
kubectl rollout restart deployment/kraken-trading-bot -n trading-bot
```

### Logs

```bash
# Docker
docker logs -f trading-bot --tail 100

# Kubernetes
kubectl logs -f deployment/kraken-trading-bot -n trading-bot --tail=100

# Logs applicatifs
tail -f trading_bot.log
```

---

## 🔍 Troubleshooting

### Problèmes Courants

#### 1. Erreur "API credentials not configured"

**Cause**: Clés API manquantes ou invalides

**Solution**:
```bash
# Vérifier variables d'environnement
echo $KRK_KEY
echo $KRK_SECRET

# Vérifier secret K8s
kubectl get secret kraken-api-keys -n trading-bot -o yaml
```

#### 2. Erreur "Insufficient margin"

**Cause**: Pas assez de marge disponible

**Solution**:
- Vérifier balance sur Kraken
- Réduire LEVERAGE
- Réduire RISK_PER_TRADE
- Fermer positions existantes

#### 3. Circuit Breaker Déclenché

**Cause**: Drawdown ou pertes excessives

**Solution**:
```bash
# Vérifier métriques
curl http://localhost:9090/metrics | grep circuit_breaker

# Reset manuel (⚠️ À utiliser avec précaution)
# Redémarrer le bot
```

#### 4. Ordres Rejetés

**Cause**: Paramètres ordre invalides

**Solution**:
- Vérifier ordermin dans AssetPairs
- Vérifier balance suffisante
- Vérifier permissions API

#### 5. Rate Limit Exceeded

**Cause**: Trop de requêtes API

**Solution**:
- Augmenter INTERVAL_SECONDS
- Le bot va automatiquement retry avec backoff

### Logs de Debug

```bash
# Activer debug logging
export LOG_LEVEL=DEBUG
python example_run.py
```

---

## 🔐 Sécurité

### Bonnes Pratiques

1. **Clés API**:
   - Créer clés avec permissions minimales
   - Restreindre par IP si possible
   - Rotation régulière (tous les 90 jours)
   - Stocker dans secret manager (Vault, AWS Secrets, etc.)

2. **Réseau**:
   - Utiliser NetworkPolicy K8s
   - Whitelist IPs Kraken
   - TLS pour communications

3. **Monitoring**:
   - Alertes sur activités suspectes
   - Logs centralisés
   - Audit trail des ordres

4. **Capital**:
   - Commencer avec petit capital
   - Limites strictes de position
   - Dry-run en premier

### Checklist Sécurité

- [ ] Clés API avec permissions limitées
- [ ] Variables d'environnement chiffrées
- [ ] NetworkPolicy configurée
- [ ] Monitoring actif
- [ ] Alertes configurées
- [ ] Backups réguliers
- [ ] Plan de disaster recovery

---

## 📞 Support

### Ressources

- **Documentation Kraken**: https://docs.kraken.com/
- **Support Kraken**: https://support.kraken.com/
- **Issues GitHub**: <repository>/issues

### Contact

En cas de problème critique:
1. Arrêter le bot immédiatement
2. Fermer positions manuellement sur Kraken si nécessaire
3. Analyser logs
4. Contacter l'équipe

---

## 📚 Annexes

### Tests

```bash
# Lancer tous les tests
python -m pytest tests/

# Test spécifique
python -m pytest tests/test_risk_engine.py -v

# Coverage
python -m pytest --cov=src tests/
```

### Backtest

```bash
# Exemple de backtest
python -c "
from src.backtest import BacktestEngine
from src.strategies import TrendFollowingStrategy
import pandas as pd

# Charger données historiques
# ...

engine = BacktestEngine(initial_capital=10000)
strategy = TrendFollowingStrategy()
results = engine.run(strategy, market_data)
print(results)
"
```

### Maintenance

- **Mise à jour dépendances**: Tous les mois
- **Revue performance**: Toutes les semaines
- **Audit sécurité**: Tous les 3 mois
- **Rotation clés**: Tous les 90 jours

---

**Version**: 1.0
**Dernière mise à jour**: 2025-01-01
**Auteur**: Trading Team
