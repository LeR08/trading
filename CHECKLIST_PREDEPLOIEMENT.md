# ✅ Checklist Pré-Déploiement
## Bot de Trading Kraken BTC avec Marge x3

**Date de déploiement prévue**: ___________
**Opérateur**: ___________
**Environnement**: [ ] DEV [ ] STAGING [ ] PRODUCTION

---

## 🔐 1. Sécurité et Conformité

### Compte Kraken

- [ ] Compte Kraken vérifié (KYC complet)
- [ ] 2FA activé sur le compte
- [ ] Email et téléphone de récupération configurés
- [ ] Notifications d'activité de compte activées
- [ ] **Marge activée** sur le compte Kraken
- [ ] Limites de compte vérifiées (deposit/withdrawal/trading)

### Clés API

- [ ] Clés API créées avec **permissions minimales**:
  - [ ] Query Funds
  - [ ] Create & Modify Orders
  - [ ] Query Open Orders & Trades
  - [ ] Query Closed Orders & Trades
  - [ ] **PAS** de permissions Withdraw Funds
- [ ] Whitelist IP configurée (si disponible)
- [ ] Clés stockées dans secret manager sécurisé
- [ ] Clés **JAMAIS** commitées dans git
- [ ] Accès aux clés limité aux personnes autorisées
- [ ] Date d'expiration/rotation planifiée (90 jours)

### Infrastructure

- [ ] Secrets Kubernetes créés et vérifiés
- [ ] NetworkPolicy configurée
- [ ] RBAC configuré (si K8s)
- [ ] Logs centralisés configurés
- [ ] Backups configurés
- [ ] Disaster recovery plan documenté

---

## 🛠️ 2. Configuration Technique

### API Kraken

- [ ] Connectivité API Kraken testée
- [ ] Endpoint `/0/public/AssetPairs` accessible
- [ ] Endpoint `/0/private/TradeBalance` accessible
- [ ] Endpoint `/0/private/AddOrder` accessible
- [ ] Rate limits Kraken compris (15-20 calls/sec)
- [ ] Gestion d'erreurs Kraken testée
- [ ] Retry logic validée

### Validation AssetPairs

- [ ] `ordermin` pour BTC/EUR récupéré et validé
- [ ] `lot_decimals` (précision volume) vérifié
- [ ] `pair_decimals` (précision prix) vérifié
- [ ] `costmin` (coût minimum ordre) vérifié
- [ ] `leverage_buy` et `leverage_sell` vérifiés
- [ ] Fees (maker/taker) actuels notés

### Validation TradeBalance

- [ ] Équité initiale notée: __________ EUR
- [ ] Margin disponible vérifié: __________ EUR
- [ ] Calcul margin level compris
- [ ] Free margin minimum défini: __________ EUR
- [ ] Formule margin level = (equity / margin_used) * 100 validée

---

## ⚙️ 3. Configuration du Bot

### Paramètres de Trading

- [ ] `PAIR` configuré (XBTEUR ou XBTUSD): __________
- [ ] `LEVERAGE` défini (1-5): __________
- [ ] Leverage autorisé sur compte Kraken vérifié
- [ ] `RISK_PER_TRADE` défini (recommandé: 0.02-0.03): __________
- [ ] `MAX_TOTAL_EXPOSURE` défini (recommandé: 0.10): __________
- [ ] `SLIPPAGE_PCT` estimé (recommandé: 0.002): __________

### Stratégie

- [ ] Stratégie sélectionnée: [ ] trend_following [ ] mean_reversion [ ] breakout
- [ ] Paramètres stratégie ajustés (EMA, RSI, etc.)
- [ ] Backtest effectué sur données historiques
- [ ] Performance backtest acceptable:
  - [ ] Win rate > 40%
  - [ ] Profit factor > 1.2
  - [ ] Max drawdown < 20%
  - [ ] Sharpe ratio > 0.5

### Risk Management

- [ ] `MAX_DRAWDOWN` défini (recommandé: 0.15): __________
- [ ] `MAX_DAILY_LOSS_PCT` défini (recommandé: 0.05): __________
- [ ] `MAX_CONSECUTIVE_LOSSES` défini (recommandé: 5): __________
- [ ] Circuit breaker testé manuellement
- [ ] Margin checker testé avec différents scénarios
- [ ] Position sizer validé avec calculs manuels

### Execution

- [ ] `MAX_RETRIES` défini (recommandé: 5): __________
- [ ] Backoff exponentiel validé
- [ ] Gestion erreurs Kraken testée:
  - [ ] Rate limit exceeded
  - [ ] Insufficient funds
  - [ ] Invalid parameters
  - [ ] Permission denied
- [ ] Ordre logs configurés (orders_log.jsonl)

---

## 🧪 4. Tests

### Tests Unitaires

- [ ] `test_risk_engine.py` passent: `python -m pytest tests/test_risk_engine.py`
- [ ] `test_executor.py` passent: `python -m pytest tests/test_executor.py`
- [ ] `test_strategies.py` passent: `python -m pytest tests/test_strategies.py`
- [ ] Coverage > 70%

### Tests d'Intégration

- [ ] Cycle complet testé en dry-run
- [ ] Récupération données marché OK
- [ ] Génération signal OK
- [ ] Calcul position size OK
- [ ] Validation ordre OK (validate=true)
- [ ] Métriques Prometheus exposées

### Tests Sandbox Kraken

- [ ] Si disponible: tests sur environnement sandbox Kraken
- [ ] Ordres test placés et vérifiés
- [ ] TP/SL testés
- [ ] Annulation ordre testée
- [ ] Fermeture position testée

### Tests de Charge

- [ ] Bot stable sur 24h en dry-run
- [ ] Pas de memory leaks
- [ ] CPU usage < 50%
- [ ] Logs propres (pas d'erreurs répétées)

---

## 📊 5. Monitoring

### Métriques Prometheus

- [ ] Endpoint `/metrics` accessible: `curl http://localhost:9090/metrics`
- [ ] Métriques exposées:
  - [ ] trading_equity
  - [ ] trading_margin_level_percent
  - [ ] trading_open_positions_total
  - [ ] trading_unrealized_pnl
  - [ ] trading_circuit_breaker_state
  - [ ] trading_total_trades
- [ ] Prometheus scraping configuré (si applicable)
- [ ] Rétention métriques configurée

### Alertes

- [ ] Alerte: Margin level < 180%
- [ ] Alerte: Circuit breaker ouvert
- [ ] Alerte: Drawdown > 12%
- [ ] Alerte: Erreurs API > seuil
- [ ] Alerte: Pod crashloop (K8s)
- [ ] Canaux notification configurés (email, Slack, PagerDuty)
- [ ] Escalade configurée

### Dashboards

- [ ] Dashboard Grafana créé (si applicable)
- [ ] Graphiques temps réel:
  - [ ] Équité
  - [ ] P&L
  - [ ] Positions
  - [ ] Margin level
  - [ ] Signal strength
- [ ] Dashboard accessible aux opérateurs

### Logs

- [ ] Logs applicatifs lisibles
- [ ] Niveau log approprié (INFO en prod)
- [ ] Logs centralisés (ELK, Loki, CloudWatch, etc.)
- [ ] Logs persistés et backupés
- [ ] Recherche logs fonctionnelle
- [ ] Alertes sur patterns d'erreur

---

## 🚀 6. Déploiement

### Dry-Run

- [ ] Bot testé 48h minimum en mode dry-run
- [ ] Tous les cycles exécutés sans erreur
- [ ] Signaux générés cohérents
- [ ] Ordres simulés corrects
- [ ] Aucun crash observé
- [ ] Métriques stables

### Image Docker

- [ ] Image buildée: `docker build -t kraken-trading-bot:v1.0 .`
- [ ] Image scannée (vulnérabilités): `docker scan kraken-trading-bot:v1.0`
- [ ] Pas de vulnérabilités critiques
- [ ] Image taguée correctement
- [ ] Image pushée dans registry: __________
- [ ] Health check fonctionnel

### Kubernetes (si applicable)

- [ ] Namespace créé: `kubectl create namespace trading-bot`
- [ ] Secrets créés et vérifiés
- [ ] ConfigMap créé et vérifié
- [ ] Deployment manifest validé
- [ ] Service créé
- [ ] NetworkPolicy appliquée
- [ ] Resource limits appropriés (CPU: 500m, RAM: 512Mi)
- [ ] Liveness/Readiness probes configurés
- [ ] Anti-affinity configurée (si replicas > 1)

### Déploiement Initial

- [ ] Déploiement effectué: `kubectl apply -f k8s/deployment.yaml`
- [ ] Pod running: `kubectl get pods -n trading-bot`
- [ ] Logs propres: `kubectl logs -f deployment/kraken-trading-bot -n trading-bot`
- [ ] Métriques accessibles: `kubectl port-forward -n trading-bot svc/kraken-bot-metrics 9090:9090`
- [ ] Sanity check: premier cycle exécuté avec succès

---

## 💰 7. Capital et Limites

### Capital Initial

- [ ] Capital initial défini: __________ EUR
- [ ] Capital = somme **acceptable à perdre** ✋
- [ ] Position size max calculée: __________ BTC
- [ ] Margin requis max calculé: __________ EUR
- [ ] Buffer de sécurité maintenu (>30% free margin)

### Limites de Levier

- [ ] Levier max Kraken pour BTC vérifié: __________
- [ ] Levier bot <= levier autorisé
- [ ] Comprendre: levier x3 = gains ET pertes x3
- [ ] Margin call level Kraken connu: __________ %
- [ ] Buffer suffisant vs margin call (>50%)

### Simulation de Scénarios

- [ ] Scénario: BTC -10% → Impact calculé: __________ EUR
- [ ] Scénario: BTC -20% → Impact calculé: __________ EUR
- [ ] Scénario: 5 pertes consécutives → Impact: __________ EUR
- [ ] Scénario: Circuit breaker déclenché → Action: __________
- [ ] Tous les scénarios dans limites acceptables

---

## 📋 8. Procédures Opérationnelles

### Documentation

- [ ] README_OPERATOR.md lu et compris
- [ ] Architecture documentée
- [ ] Runbooks créés:
  - [ ] Démarrage bot
  - [ ] Arrêt bot
  - [ ] Changement stratégie
  - [ ] Rotation clés API
  - [ ] Réponse incident
- [ ] Contact d'escalade documentés

### Équipe

- [ ] Équipe formée sur le bot
- [ ] Au moins 2 personnes peuvent opérer le bot
- [ ] Astreinte définie (si production)
- [ ] Playbooks accessibles 24/7

### Plan de Reprise

- [ ] Procédure arrêt d'urgence documentée
- [ ] Procédure fermeture manuelle positions documentée
- [ ] Backup configuration disponible
- [ ] Contact Kraken support connu
- [ ] Procédure rollback testée

---

## 🔄 9. Conformité et Légal

### Réglementation

- [ ] Vérifier légalité trading algorithmique dans juridiction: __________
- [ ] Vérifier obligations déclaration fiscale
- [ ] Vérifier conformité MiFID II / MiCA (si UE)
- [ ] Consultation avocat/fiscaliste si montants importants
- [ ] Assurance cyber / responsabilité civile évaluée

### Audit Trail

- [ ] Tous ordres loggés avec timestamp
- [ ] Logs conservés minimum 5 ans (réglementation)
- [ ] Logs immutables / tamper-proof
- [ ] Procédure export logs pour audit

---

## ✅ 10. Validation Finale

### Sign-off

- [ ] Tous les items critiques (🔴) complétés
- [ ] Risques résiduels identifiés et acceptés
- [ ] Dry-run validé par: __________ Date: __________
- [ ] Configuration revue par: __________ Date: __________
- [ ] Sécurité validée par: __________ Date: __________

### Go / No-Go

**Décision de déploiement**:
- [ ] ✅ GO - Tous les critères remplis
- [ ] ❌ NO-GO - Raison: __________

**Signatures**:
- Opérateur: __________ Date: __________
- Responsable Technique: __________ Date: __________
- Responsable Risques: __________ Date: __________

---

## 📝 Notes Additionnelles

```
[Espace pour notes spécifiques au déploiement]












```

---

## ⚠️ RAPPELS IMPORTANTS

1. **Le trading comporte des risques de perte en capital**
2. **Le leverage amplifie gains ET pertes**
3. **Commencer avec petit capital**
4. **Surveiller quotidiennement**
5. **Avoir un plan de sortie**
6. **Ne jamais trader argent qu'on ne peut perdre**
7. **En cas de doute: ARRÊTER le bot**

---

**Version**: 1.0
**Dernière mise à jour**: 2025-01-01
**Prochaine revue**: __________
