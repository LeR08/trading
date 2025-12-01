# 🚀 Guide Démarrage Rapide - Petit Capital (26$)

Guide pour tester le bot de trading avec un petit capital de 26$ et levier 10x.

## 💰 Avec 26$ et Levier 10x

### Ce que vous pouvez faire :
- **Capital disponible** : 26 USD
- **Pouvoir d'achat avec levier 10x** : 260 USD
- **Risque par trade (1%)** : 0.26 USD
- **Perte maximale journalière (3%)** : 0.78 USD
- **Drawdown max avant arrêt (20%)** : 5.20 USD

### 📊 Exemple de trade :
Avec BTC à 95,000$ :
- Position : 0.00274 BTC (260$ avec levier 10x)
- Margin requis : 26$
- Si BTC monte de +2% : Vous gagnez +5.20$ (+20%)
- Si BTC baisse de -2% : Vous perdez -5.20$ (-20%)

## ⚙️ Configuration Optimale pour 26$

### 1. Créer le fichier `.env`

```bash
copy .env.example .env
notepad .env
```

### 2. Configuration recommandée

```env
# Vos clés API Kraken
KRK_KEY=votre_cle_api
KRK_SECRET=votre_secret_api

# Trading BTC/USD avec levier 10x
PAIR=XBTUSD
LEVERAGE=10

# Risque 1% = 0.26$ par trade
RISK_PER_TRADE=0.01

# Stratégie
STRATEGY=trend_following

# Protection
MAX_DRAWDOWN=0.20           # Stop si -20% (-5.20$)
MAX_DAILY_LOSS_PCT=0.03     # Stop si -3% par jour (-0.78$)
MAX_CONSECUTIVE_LOSSES=3     # Stop après 3 pertes

# Mode
DRY_RUN=true                # Commencer en simulation!
INTERVAL_SECONDS=300        # Vérifier toutes les 5 minutes
```

## 🚀 Lancer le Bot

```bash
# Mode dry-run (simulation)
python example_run.py
```

## 📈 Que va faire le bot ?

### Cycle de trading :

1. **Récupère le prix BTC** toutes les 5 minutes
2. **Analyse la tendance** avec les indicateurs (EMA, MACD, RSI)
3. **Génère un signal** : BUY, SELL ou HOLD
4. **Calcule la taille** de position (environ 0.002-0.003 BTC)
5. **Vérifie les risques** :
   - Margin suffisant ?
   - Drawdown dans les limites ?
   - Circuit breaker OK ?
6. **Place l'ordre** (en simulation d'abord)

### Exemple de sortie console :

```
[CYCLE] NOUVEAU CYCLE - 2025-12-01 17:00:00
============================================================

[DOWN] 1. Récupération données marché...
   Prix actuel BTC: 95,234.50 USD

[TARGET] 2. Génération signal de trading...
   Signal: BUY
   Confiance: 75.3%
   Raison: Tendance haussière confirmée: EMA alignment + MACD bullish
   TP: 96,142.67 | SL: 94,326.33

[MONEY] 3. Vérification balance et marge...
   Équité: 26.00 USD
   Margin Level: inf%
   Free Margin: 26.00 USD

[LOCK] 4. Vérification circuit breaker...
   État: closed
   Drawdown: 0.00%

[RULER] 6. Calcul taille position...
   Volume: 0.00273 BTC
   Valeur position: 260.00 USD
   Margin requis: 26.00 USD
   Leverage: 10x

[*] 7. Placement de l'ordre...
[!] MODE DRY-RUN: L'ordre ne sera PAS réellement placé
   Side: BUY
   Volume: 0.00273 BTC
   Pair: XBTUSD
   Leverage: 10x
   Take Profit: 96,142.67
   Stop Loss: 94,326.33
[OK] Ordre simulé avec succès
```

## 📊 Métriques en Temps Réel

Pendant que le bot tourne, consultez les métriques :
- Ouvrez votre navigateur : http://localhost:9090/metrics

Vous verrez :
- `trading_equity` : Votre capital actuel
- `trading_margin_level_percent` : Niveau de marge
- `trading_signal_strength` : Force du signal (0-1)
- `trading_circuit_breaker_state` : État du circuit breaker

## ⚠️ Protections Activées

### 1. Circuit Breaker
- **Drawdown > 20%** : Stop automatique si vous perdez 5.20$
- **Perte journalière > 3%** : Stop si -0.78$ dans la journée
- **3 pertes consécutives** : Pause automatique

### 2. Stop Loss Automatique
- Chaque position a un SL automatique
- Limite la perte à environ 2% par trade

### 3. Margin Checker
- Vérifie avant chaque trade si assez de marge
- Empêche les margin calls

## 🎯 Objectifs Réalistes avec 26$

### Scénario Conservateur (1 mois)
- **Objectif** : +15% (+3.90$) = 29.90$
- **Trades gagnants** : 60% win rate
- **Risque** : Peut perdre -20% (-5.20$) = 20.80$

### Scénario Agressif (1 mois)
- **Objectif** : +50% (+13$) = 39$
- **Trades gagnants** : 65% win rate
- **Risque** : Peut perdre -20% (-5.20$) = 20.80$

## 📝 Checklist Avant de Trader en Réel

- [ ] ✅ Testé en dry-run pendant au moins 3 jours
- [ ] ✅ Compris le fonctionnement du levier 10x
- [ ] ✅ Vérifié que les clés API fonctionnent
- [ ] ✅ Capital = argent que vous pouvez perdre
- [ ] ✅ Surveillé les métriques Prometheus
- [ ] ✅ Lu et compris les warnings de risque

## 🔄 Passer en Mode Réel

**⚠️ ATTENTION** : Seulement après plusieurs jours de tests en dry-run !

Dans `.env`, changer :
```env
DRY_RUN=false
```

## 💡 Conseils

1. **Commencez en dry-run** au moins 3-7 jours
2. **Surveillez chaque jour** les premiers jours
3. **Notez les performances** dans un tableau
4. **Soyez patient** : Le bot trade seulement si signal > 60%
5. **Acceptez les pertes** : Elles font partie du trading

## 🆘 En Cas de Problème

### Le bot ne trade pas
- Normal ! Il attend un signal > 60% de confiance
- Le marché peut être en consolidation (pas de tendance)
- Patience : Peut prendre plusieurs cycles avant un trade

### Erreur "Invalid Key"
- Vérifiez vos clés API dans `.env`
- Permissions correctes sur Kraken ?

### Margin insuffisant
- Capital < 26$ ?
- Augmentez votre dépôt ou réduisez le levier

## 📚 Ressources

- **Métriques** : http://localhost:9090/metrics
- **Logs** : Fichier `trading_bot.log`
- **Documentation** : `README_OPERATOR.md`
- **Checklist** : `CHECKLIST_PREDEPLOIEMENT.md`

---

**BON TRADING ! 🚀**

*Rappelez-vous : Le trading comporte des risques. Ne tradez que l'argent que vous pouvez vous permettre de perdre.*
