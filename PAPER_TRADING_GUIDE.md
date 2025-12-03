# 📝 Guide du Mode Paper Trading & Suivi des Positions

## 🎯 Nouvelles Fonctionnalités

### 1. Mode Paper Trading (Fictif)

Le mode **Paper Trading** vous permet de tester le bot sans risquer d'argent réel. Toutes les positions sont simulées avec les prix réels du marché.

#### ✅ Avantages
- **Aucun risque financier** - Pas d'argent réel en jeu
- **Tests de stratégies** - Testez vos configurations avant de passer en réel
- **Suivi réaliste** - Utilise les vrais prix du marché Kraken
- **TP/SL automatiques** - Simule l'exécution des Take Profit et Stop Loss

#### 📊 Fonctionnalités en Paper Trading
- Simulation complète des trades
- Calcul du P&L en temps réel
- Tracking des positions virtuelles
- Notifications Discord des positions
- Exécution automatique des TP/SL

### 2. Suivi des Positions en Temps Réel

Le bot surveille maintenant toutes vos positions ouvertes et affiche leur état.

#### 📈 Informations affichées
- **Side**: BUY ou SELL
- **Volume**: Taille de la position en BTC
- **Entry Price**: Prix d'entrée
- **Current Price**: Prix actuel
- **Leverage**: Effet de levier utilisé
- **P&L**: Profit/Loss en USD et en %
- **Status**: État de la position

#### 🎨 Status des positions
- ✅ **PROFIT** - Position en gain
- 🔴 **LOSS** - Position en perte
- 🎯 **NEAR TP** - Proche du Take Profit (>80%)
- ⚠️ **NEAR SL** - Proche du Stop Loss (>80%)
- ➖ **NEUTRAL** - Position à l'équilibre

## 🚀 Utilisation

### Démarrage du Bot

Lancez le bot normalement :

```bash
python pro_trading_bot.py
```

### Sélection du Mode

Au démarrage, le bot vous demande de choisir le mode :

```
╔═══════════════════════════════════════╗
║     TRADING MODE SELECTION            ║
╚═══════════════════════════════════════╝

1. 📝 PAPER TRADING (Mode Fictif - Simulation)
   - No real money at risk
   - Perfect for testing strategies
   - Simulates trades and tracks P&L

2. 💰 LIVE TRADING (Mode Réel)
   - REAL MONEY - REAL TRADES
   - Executes actual orders on Kraken
   - Use with caution!

Default from .env: PAPER TRADING

Choose mode (1=Paper, 2=Live, or press ENTER for default):
```

#### Options :
- **Tapez `1`** : Mode Paper Trading (recommandé pour débuter)
- **Tapez `2`** : Mode Live Trading (argent réel, demande confirmation)
- **Appuyez sur ENTER** : Utilise le mode par défaut du `.env`

### Configuration via .env

Vous pouvez aussi définir le mode par défaut dans le fichier `.env` :

```bash
# Mode de trading: true pour mode fictif, false pour mode réel
PAPER_TRADING=true
```

## 📊 Affichage des Positions

Le bot affiche l'état des positions **toutes les 3 itérations** :

```
======================================================================
📊 OPEN POSITIONS (2)
======================================================================

1. Position BUY - ✅ PROFIT
   Volume: 0.0500 BTC
   Entry: $93,000.00
   Current: $93,500.00
   Leverage: 10x
   P&L: +$25.00 (+5.37%)
   Value: $4,675.00

2. Position SELL - 🔴 LOSS
   Volume: 0.0300 BTC
   Entry: $93,200.00
   Current: $93,500.00
   Leverage: 10x
   P&L: -$9.00 (-3.22%)
   Value: $2,805.00

──────────────────────────────────────────────────────────────────────
Total P&L: +$16.00
Average P&L: +1.08%
======================================================================
```

### Sur Discord

Les positions sont aussi envoyées sur Discord avec des embeds colorés :

- 🟢 **Vert** : P&L positif
- 🔴 **Rouge** : P&L négatif
- ⚪ **Gris** : P&L neutre

## 🎓 Mode Paper Trading en Détail

### Comment ça marche ?

1. **Signal détecté** → Le bot crée une position virtuelle
2. **Suivi en temps réel** → Le bot surveille le prix du marché
3. **TP/SL automatiques** → Si le prix atteint le TP ou SL, la position se ferme automatiquement
4. **Calcul du P&L** → Le bot calcule les profits/pertes comme si c'était réel

### Exemple de Paper Trade

```
📝 EXECUTING PAPER TRADE (SIMULATION)
✅ Paper position opened: PAPER_1

SIGNAL DETAILS SENT (PAPER):
   Action: BUY
   Pair: BTC/USD
   Leverage: 10x
   Size: 0.05 BTC
   Entry: $93,023.90
   TP: $97,675.10 (+5%)
   SL: $91,163.42 (-2%)
   Confidence: 85%
```

### Fermeture Automatique

Le bot surveille automatiquement vos positions paper :

```
2025-12-03 21:45:12 - PositionTracker - INFO - Paper position PAPER_1 hit TP!
```

## 💰 Mode Live Trading

### ⚠️ Avertissements

Le mode Live Trading utilise de l'**argent réel** !

- Tous les trades sont **réellement exécutés** sur Kraken
- Les pertes sont **réelles**
- Utilisez uniquement après avoir testé en Paper Trading
- Commencez avec de **petites sommes**

### Confirmation Requise

Pour activer le Live Trading, vous devez :

1. Choisir l'option `2` au démarrage
2. Taper **`CONFIRM`** pour confirmer

```
Choose mode (1=Paper, 2=Live, or press ENTER for default): 2

⚠️  WARNING: Live trading uses REAL MONEY! Type 'CONFIRM' to proceed: CONFIRM

✅ Mode selected: LIVE TRADING (RÉEL)
```

### Sécurité en Live Mode

Par défaut, même en Live Mode, le bot **N'EXÉCUTE PAS** automatiquement les trades. Il envoie seulement les signaux.

Pour activer l'exécution automatique, décommentez la ligne dans `pro_trading_bot.py` (ligne ~349) :

```python
# Uncomment line below to enable automatic live trading:
# self.execute_trade(signal_data)
```

## 🔄 Passage entre les Modes

### Paper → Live

1. Arrêtez le bot (Ctrl+C)
2. Relancez : `python pro_trading_bot.py`
3. Choisissez option `2` (Live Trading)
4. Confirmez avec `CONFIRM`

### Live → Paper

1. Arrêtez le bot (Ctrl+C)
2. Relancez : `python pro_trading_bot.py`
3. Choisissez option `1` (Paper Trading)

## 📱 Notifications Discord

### Signaux de Trading

Tous les signaux sont envoyés sur Discord avec indication du mode :

```
📈 BUY SIGNAL - BTC/USD 🔥🔥
[PAPER TRADING MODE]
```

### Statut des Positions

Toutes les 3 itérations, le bot envoie un récapitulatif :

```
📝 Position Status Update - PAPER TRADING

📊 Summary
Total Positions: 2
Total P&L: +$16.00
Average P&L: +1.08%

📈 Position #1 - 0.0500 BTC
Side: BUY | Leverage: 10x
Entry: $93,000.00
Current: $93,500.00
P&L: +$25.00 (+5.37%)
Status: ✅ PROFIT
```

## 💡 Conseils

### Pour débuter
1. ✅ **Commencez toujours en Paper Trading**
2. ✅ Testez vos configurations pendant plusieurs jours
3. ✅ Analysez les résultats des positions simulées
4. ✅ Ajustez vos paramètres (TP, SL, confidence score)
5. ✅ Seulement ensuite, passez en Live avec prudence

### Paramètres recommandés pour débuter
```bash
PAPER_TRADING=true
TAKE_PROFIT_PERCENT=5.0
STOP_LOSS_PERCENT=2.0
MIN_CONFIDENCE_SCORE=75
MAX_OPEN_POSITIONS=2
```

### Analyse des performances
- Surveillez le ratio Gagnant/Perdant
- Notez les conditions où le bot performe le mieux
- Ajustez les timeframes si nécessaire
- Testez différents niveaux de confidence minimum

## 🆘 Problèmes courants

### "No open positions" alors que j'ai des positions paper
- Normal si c'est une nouvelle session
- Les positions paper ne persistent pas entre les redémarrages
- Solution : Laissez le bot tourner en continu

### Le bot ne crée pas de positions
- Vérifiez le `MIN_CONFIDENCE_SCORE` (peut-être trop élevé)
- Vérifiez `MAX_OPEN_POSITIONS`
- Regardez les logs pour voir pourquoi les signaux sont rejetés

### Discord ne reçoit pas les mises à jour de positions
- Les positions sont envoyées toutes les 3 itérations
- Vérifiez que vous avez des positions ouvertes
- Vérifiez les logs pour les erreurs webhook

## 📚 En Résumé

| Feature | Paper Trading | Live Trading |
|---------|---------------|--------------|
| Argent réel | ❌ Non | ✅ Oui |
| Exécution trades | Simulé | Réel |
| Suivi positions | ✅ Oui | ✅ Oui |
| Webhook Discord | ✅ Oui | ✅ Oui |
| TP/SL auto | Simulé | Réel |
| Risque financier | ❌ Aucun | ⚠️ Élevé |
| Recommandé pour | Tests, apprentissage | Trading réel |

---

**🎯 Recommandation**: Utilisez le Paper Trading pendant au moins 1 semaine avant de considérer le Live Trading !
