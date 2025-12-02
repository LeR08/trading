# Web Dashboard - Guide d'utilisation

## 🎯 Vue d'ensemble

Le dashboard web vous permet de:
- **Contrôler le bot** en temps réel (Start/Stop)
- **Choisir le mode** (Paper/Live) via l'interface
- **Visualiser les métriques** (Equity, Marge, P&L)
- **Voir les trades en direct**
- **Ajuster la configuration** pour être plus agressif

## 🚀 Démarrage

### 1. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 2. Lancer le bot avec le dashboard

```bash
python run_with_web.py
```

### 3. Accéder au dashboard

Ouvrez votre navigateur:
```
http://localhost:8080
```

## 📊 Interface

### En-tête
- **Mode Selector**: Basculer entre Paper (📝) et Live (🔴)
- **Boutons de contrôle**:
  - ▶️ **Start**: Démarre le bot
  - ⏹️ **Stop**: Arrête le bot

### Cartes de métriques
1. **Status**: État du bot (Running/Stopped) + numéro d'itération
2. **Equity**: Capital total disponible
3. **Margin Free**: Marge disponible pour de nouveaux trades
4. **Open Positions**: Nombre de positions ouvertes
5. **Daily P&L**: Profit/Perte du jour (vert si positif, rouge si négatif)
6. **Total P&L**: Profit/Perte total

### Configuration Agressive

Pour obtenir 5-10 trades par jour, utilisez ces paramètres recommandés:

| Paramètre | Valeur Recommandée | Description |
|-----------|-------------------|-------------|
| **Confidence Threshold** | 50% | Seuil de confiance minimum (plus bas = plus de trades) |
| **Risk Per Trade** | 2% | Risque par trade (2% de l'equity) |
| **Max Concurrent Trades** | 5 | Nombre maximum de positions simultanées |
| **Leverage** | 3x | Effet de levier |

Cliquez sur **Update Configuration** après avoir modifié les valeurs.

### Tableau des Trades

Affiche toutes les positions ouvertes avec:
- **ID**: Identifiant du trade
- **Direction**: LONG (vert) ou SHORT (rouge)
- **Entry**: Prix d'entrée
- **Volume**: Quantité de BTC
- **Stop Loss**: Prix de stop loss
- **Take Profit**: Prix de take profit
- **P&L**: Profit/Perte actuel
- **Time**: Heure d'ouverture

## ⚡ Configuration Agressive (5-10 trades/jour)

### Fichier de configuration pré-configuré

Utilisez `config_aggressive.yaml` pour un mode agressif:

```bash
# Copiez la config aggressive
cp config/config_aggressive.yaml config/config.yaml

# Relancez le bot
python run_with_web.py
```

### Différences avec le mode conservateur

| Paramètre | Conservateur | Agressif |
|-----------|-------------|----------|
| Confidence Threshold | 66% | 50% |
| Risk Per Trade | 1% | 2% |
| Max Concurrent Trades | 3 | 5 |
| Refresh Interval | 40s | 30s |
| SL ATR Multiplier | 1.0 | 0.8 (plus serré) |
| TP Reward Ratio | 0.7 | 0.6 (profits rapides) |
| Max Trade Duration | 30min | 20min |

### Pourquoi ces paramètres génèrent plus de trades?

1. **Seuil de confiance réduit (50%)**: Plus de signaux passent le filtre
2. **Refresh plus rapide (30s)**: Détection plus fréquente des opportunités
3. **Plus de positions simultanées (5)**: Peut ouvrir plusieurs trades en parallèle
4. **Stop Loss plus serré (0.8 ATR)**: Sorties plus rapides = turnover accru
5. **Take Profit plus rapide (0.6)**: Clôture rapide des positions gagnantes

## 🔄 Mises à jour en temps réel

Le dashboard se rafraîchit automatiquement:
- **Status & Métriques**: Toutes les 2 secondes
- **Liste des trades**: Toutes les 3 secondes
- **WebSocket**: Notifications instantanées

## ⚠️ Circuit Breaker

Si le circuit breaker s'active (drawdown trop important):
1. Un bandeau rouge apparaît en haut
2. Le trading s'arrête automatiquement
3. Cliquez sur **Reset** pour réactiver (après avoir analysé le problème)

## 🔐 Sécurité

### Mode Paper (Recommandé pour tester)

1. Sélectionnez **📝 Paper** dans le header
2. Cliquez sur **Start**
3. Le bot simule les trades sans argent réel

### Mode Live (Production)

⚠️ **ATTENTION**: Utilise de l'argent réel!

1. Assurez-vous d'avoir:
   - Testé en Paper pendant 2-4 semaines
   - Validé les performances en backtest
   - Configuré les clés API dans `.env`
2. Sélectionnez **🔴 Live**
3. Cliquez sur **Start**

## 📱 API REST

Le dashboard expose une API REST complète:

### Endpoints disponibles

```
GET  /api/status              - État du bot
GET  /api/trades              - Liste des trades ouverts
POST /api/config              - Mettre à jour la configuration
POST /api/start               - Démarrer le bot
POST /api/stop                - Arrêter le bot
POST /api/circuit-breaker/reset - Réinitialiser le circuit breaker
WS   /ws                      - WebSocket pour updates en temps réel
```

### Exemple d'utilisation avec curl

```bash
# Obtenir le status
curl http://localhost:8080/api/status

# Démarrer le bot
curl -X POST http://localhost:8080/api/start

# Mettre à jour la config
curl -X POST http://localhost:8080/api/config \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "paper",
    "confidence_threshold": 0.5,
    "risk_per_trade": 0.02,
    "max_concurrent_trades": 5,
    "leverage": 3
  }'
```

## 🐛 Dépannage

### Le dashboard ne se charge pas

1. Vérifiez que le bot est lancé: `python run_with_web.py`
2. Vérifiez le port: `http://localhost:8080`
3. Vérifiez les logs dans la console

### Pas de trades générés

1. Vérifiez le seuil de confiance (essayez 50%)
2. Vérifiez que le bot est bien en mode Running
3. Regardez les logs pour voir les signaux générés
4. Le marché peut être en range (peu de signaux valides)

### Mode Live ne fonctionne pas

1. Vérifiez `.env` contient `KRK_KEY` et `KRK_SECRET`
2. Vérifiez les permissions API (trading activé)
3. Vérifiez le solde disponible sur Kraken
4. Testez d'abord en mode Paper!

## 📈 Conseils pour 5-10 trades/jour

1. **Commencez en Paper**: Testez la configuration agressive 1 semaine
2. **Surveillez le drawdown**: Si > 5% par jour, réduisez risk_per_trade
3. **Ajustez le seuil**:
   - Trop de trades perdants? Augmentez à 55-60%
   - Pas assez de trades? Baissez à 45%
4. **Heures actives**: Le bot trade mieux pendant les heures de forte volatilité (13h-22h UTC)
5. **Weekends**: Moins de volatilité = moins de trades

## 🎨 Personnalisation

Le dashboard est entièrement contenu dans `/src/web/api.py`. Vous pouvez modifier:
- Les couleurs (section `<style>`)
- Les métriques affichées
- La fréquence de rafraîchissement
- Les endpoints API

## 🔗 Intégration externe

Vous pouvez intégrer le bot avec:
- **Grafana**: Via l'endpoint Prometheus (port 8000)
- **Webhooks**: Modifiez `broadcast_update()` pour envoyer à vos services
- **Trading View**: Via l'API REST pour recevoir des signaux

---

**Bon trading! 🚀📈**
