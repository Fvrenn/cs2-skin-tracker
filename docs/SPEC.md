# SPEC.md — Cahier des charges fonctionnel

## Objectif du projet
Plateforme de tracking de skins CS2 permettant à un groupe d'amis (max 5 users simultanés) de surveiller la valeur de leurs skins et d'être alertés au bon moment pour vendre au meilleur prix — sans rester collés aux graphiques.

---

## Utilisateurs
- 5 utilisateurs maximum en simultané
- Chaque user a son propre compte, ses propres skins, ses propres alertes
- Pas de rôle admin spécifique en V1 — chaque user gère ses propres paramètres

---

## Fonctionnalités par page

### `/login`
- Authentification email + mot de passe via Better Auth
- Pas d'inscription publique (invitation uniquement ou création manuelle en V1)

### `/dashboard`
- Valeur totale du portefeuille en temps réel
- Graphique d'évolution de la valeur totale du portefeuille dans le temps
- P&L global (profit/perte total en € et en %)
- Liste des skins en alerte mis en avant (badge 🔴)
- Résumé des dernières alertes reçues

### `/skins`
- Liste de tous les skins de l'inventaire Steam de l'user
- Badge statut par skin :
  - 🟢 STABLE — prix normal
  - 🟡 EN HAUSSE — seuil de bénéf atteint, surveillance active
  - 🔴 ALERTE — retournement détecté, vendre
  - ⚫ VENDU — skin disparu de l'inventaire
- Prix actuel, prix d'achat, P&L en € et %
- Bouton refresh manuel de l'inventaire Steam

### `/skins/[id]`
- Image du skin
- Graphique historique des prix (toutes les 5 min, depuis le début)
- Tableau P&L détaillé :
  - Prix d'achat (saisi manuellement)
  - Prix actuel
  - Pic historique atteint
  - Bénéfice potentiel actuel
- Lien direct vers le listing CSFloat
- Historique des alertes reçues pour ce skin

### `/market`
- Explorer tous les skins CS2 disponibles sur CSFloat
- Filtres : nom, catégorie, fourchette de prix
- Prix live min/max/médian (Skinport + CSFloat)
- Bouton "Ajouter à la Watchlist" avec configuration des seuils

### `/settings`
- Steam ID (pour l'import inventaire)
- Discord ID (pour les MP d'alerte)
- Seuils d'alerte personnalisés :
  - Seuil hausse (défaut : +25% vs prix d'achat)
  - Seuil retournement (défaut : -10% vs pic récent)
  - Seuil rappel baisse continue (défaut : 2 jours / 7 jours)

---

## Logique de l'algorithme d'alerte

### Machine à états par skin

```
ÉTAT 1 — PASSIF
  Condition : prix actuel < prix_achat × (1 + seuil_hausse)
  Action     : collecte silencieuse des données toutes les 5 min
  Transition : → ACTIF si prix dépasse le seuil

ÉTAT 2 — ACTIF (pic surveillé)
  Condition : prix actuel >= prix_achat × (1 + seuil_hausse)
  Action     : mise à jour du pic_price si prix actuel > pic connu
               envoi MP Discord "🚀 [Skin] a pris +X%, surveille le pic !"
               (une seule fois à l'entrée dans cet état)
  Transition : → ALERTE si prix <= pic_price × (1 - seuil_retournement)

ÉTAT 3 — ALERTE VENTE
  Condition : prix actuel <= pic_price × (1 - seuil_retournement)
  Action     : envoi MP Discord "🔴 [Skin] redescend de -10%, pense à vendre !"
  Transition : → RAPPEL si baisse continue

ÉTAT 4 — RAPPEL
  Condition : baisse continue sur 2j ou baisse significative sur 7j
  Action     : re-notification MP Discord avec comparaison J-2 et J-7
  Transition : → VENDU si skin disparu de l'inventaire Steam
```

### Détection de vente
- Toutes les 5 min, le bot compare l'inventaire Steam stocké en BDD avec l'inventaire actuel
- Si un skin n'est plus présent → statut `VENDU`, plus d'alertes, archivage des données

### Watchlist (skins non possédés)
- **Alerte achat** : si prix actuel <= seuil_drop défini par l'user → MP Discord "💰 Opportunité d'achat"
- **Alerte trend** : si prix a augmenté de X% sur 24h → MP Discord "📈 Trend détecté"

---

## Format des alertes Discord (MP privé)

### Alerte hausse (entrée état ACTIF)
```
🚀 OPPORTUNITÉ — AK-47 | Redline (Field-Tested)

💰 Prix actuel : 85 €
🛒 Prix d'achat : 60 €
📈 Bénéfice : +41.7% (+25 €)
📊 Pic sur 7j : 87 €

👉 Voir sur CSFloat : https://csfloat.com/...
```

### Alerte vente (entrée état ALERTE)
```
🔴 VENDS MAINTENANT — AK-47 | Redline (Field-Tested)

📉 Retournement détecté : -10% depuis le pic
📊 Pic atteint : 87 € → Prix actuel : 78 €
💰 Bénéfice restant : +30% vs prix d'achat

👉 Voir sur CSFloat : https://csfloat.com/...
```

### Rappel baisse continue
```
⚠️ RAPPEL — AK-47 | Redline (Field-Tested)

📉 Baisse continue depuis 2 jours
📊 Il y a 2j : 78 € → Maintenant : 72 €
💸 Perte depuis le pic : -17%

👉 Voir sur CSFloat : https://csfloat.com/...
```

---

## Contraintes techniques

| Contrainte | Détail |
|---|---|
| Polling CSFloat | Toutes les 5 min (cache 5 min Skinport) |
| Refresh inventaire Steam | Manuel uniquement (bouton dans l'interface) |
| Historique BDD | Conservé indéfiniment |
| Utilisateurs max | 5 simultanés |
| Alertes Discord | MP privé par user (nécessite Discord ID) |
| Prix d'achat | Saisi manuellement par l'user dans l'interface |

---

## Ce qui est hors scope V1
- Vente automatique sur CSFloat
- Notifications push mobile
- Import CSV de portefeuille
- Partage de portefeuille entre users
- Analyse multi-users / classement entre amis
