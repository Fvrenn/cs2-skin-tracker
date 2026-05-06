# API.md — APIs externes

## CSFloat API

**Base URL** : `https://csfloat.com/api/v1`  
**Auth** : `Authorization: <API-KEY>` dans les headers  
**Doc** : https://docs.csfloat.com

### Endpoints utilisés

#### `GET /listings` — Prix live d'un skin
```
Params :
  market_hash_name  string   Nom exact du skin (ex: "AK-47 | Redline (Field-Tested)")
  sort_by           string   lowest_price | best_deal
  limit             int      Max 50
  type              string   buy_now

Réponse clé :
  [].price              → Prix en centimes
  [].item.float_value   → Float du skin
  [].item.scm.price     → Prix Steam Community Market en centimes
```

#### `POST /listings` — Mettre en vente (V2 future)
```
Body :
  asset_id   string   Steam asset ID du skin
  type       string   buy_now
  price      int      Prix en centimes
```

### Stratégie de polling
- Toutes les 5 minutes
- 1 requête par `market_hash_name` distinct (regrouper les skins identiques)
- Espacer les requêtes de 2 secondes entre chaque appel
- Logger les 429 et backoff exponentiel si rate limit atteint

---

## Skinport API

**Base URL** : `https://api.skinport.com/v1`  
**Auth** : Aucune pour les endpoints publics  
**Header obligatoire** : `Accept-Encoding: br`  
**Doc** : https://docs.skinport.com

### Endpoints utilisés

#### `GET /items` — Prix actuels de tous les skins
```
Params :
  app_id    int      730 (CS2)
  currency  string   EUR
  tradable  bool     false (inclure non-tradables)

Cache : 5 minutes côté Skinport
Rate limit : 8 req / 5 min

Réponse clé (par item) :
  market_hash_name  → Identifiant du skin
  suggested_price   → Prix suggéré en EUR
  min_price         → Prix minimum listé
  max_price         → Prix maximum listé
  mean_price        → Prix moyen
  median_price      → Prix médian
  quantity          → Nombre de listings actifs
```

#### `GET /sales/history` — Historique des ventes
```
Params :
  market_hash_name  string   Noms séparés par des virgules
  app_id            int      730
  currency          string   EUR

Cache : 5 minutes côté Skinport
Rate limit : 8 req / 5 min

Réponse clé (par item) :
  last_24_hours.{min, max, avg, median, volume}
  last_7_days.{min, max, avg, median, volume}
  last_30_days.{min, max, avg, median, volume}
  last_90_days.{min, max, avg, median, volume}
```

### Notes
- Les prix Skinport sont en **EUR** (float), pas en centimes → multiplier par 100 avant stockage BDD
- Si `min_price` est `null` → item hors stock sur Skinport

---

## Steam API

### Inventaire public
```
GET https://steamcommunity.com/inventory/<STEAM_ID>/730/2

Params :
  l         string   english
  count     int      5000 (max)

Pas d'auth requise si inventaire public
Rate limit : souple, 1 req / 2 sec conseillé

Réponse clé :
  assets[].assetid          → Asset ID unique de l'item
  assets[].classid          → Class ID (pour join avec descriptions)
  descriptions[].market_hash_name → Nom du skin
  descriptions[].icon_url   → URL de l'image
```

### Historique des prix (backfill)
```
GET https://steamcommunity.com/market/pricehistory/

Params :
  appid             int      730
  market_hash_name  string   Nom exact du skin
  currency          int      3 (EUR)

Auth : Cookie steamLoginSecure requis
Rate limit : STRICT — 1 req / 3 sec minimum, sinon ban temporaire

Réponse :
  prices: [
    ["Apr 15 2021 01: +0", 12.45, "142"],
    ...
  ]
  Format : [date_string, prix_median_EUR, volume_string]
```

### Parsing du format date Steam
```python
from datetime import datetime

def parse_steam_date(date_str: str) -> datetime:
    # Format: "Apr 15 2021 01: +0"
    cleaned = date_str.replace(": +0", "").strip()
    return datetime.strptime(cleaned, "%b %d %Y %H")
```

### Clé API Steam
- Obtenir sur : https://steamcommunity.com/dev/apikey
- Utilisée pour certains endpoints (profil, etc.)
- Le `steamLoginSecure` cookie est différent de la clé API

---

## Discord Bot

**Doc** : https://discord.com/developers/docs  
**Lib Python** : `discord.py` ou appels HTTP directs via `httpx`

### Setup bot
1. Créer une application sur https://discord.com/developers/applications
2. Créer un bot et récupérer le `DISCORD_BOT_TOKEN`
3. Permissions requises : `Send Messages`, `Read Message History`
4. L'user doit partager un serveur avec le bot pour recevoir des DMs
5. L'user renseigne son `discord_id` dans les settings de l'app

### Envoi d'un MP privé
```python
import httpx

async def send_discord_dm(discord_id: str, message: str) -> bool:
    """
    Envoie un MP privé à un user Discord.
    Retourne True si succès, False si échec.
    """
    headers = {"Authorization": f"Bot {DISCORD_BOT_TOKEN}"}

    # 1. Créer un DM channel
    async with httpx.AsyncClient() as client:
        dm_response = await client.post(
            "https://discord.com/api/v10/users/@me/channels",
            headers=headers,
            json={"recipient_id": discord_id}
        )
        if dm_response.status_code != 200:
            return False

        channel_id = dm_response.json()["id"]

        # 2. Envoyer le message
        msg_response = await client.post(
            f"https://discord.com/api/v10/channels/{channel_id}/messages",
            headers=headers,
            json={"content": message}
        )
        return msg_response.status_code == 200
```

### Format des messages Discord
- Utiliser les **embeds Discord** pour un rendu plus propre (optionnel en V1)
- Emojis supportés nativement : 🚀 🔴 ⚠️ 💰 📈 📉
- Limite : 2000 caractères par message

---

## Gestion des erreurs API

### Pattern standard pour tous les clients
```python
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=60)
)
async def fetch_with_retry(url: str, **kwargs) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(url, **kwargs)

        if response.status_code == 429:
            raise RateLimitError(f"Rate limit on {url}")
        if response.status_code >= 500:
            raise ServerError(f"Server error on {url}: {response.status_code}")

        response.raise_for_status()
        return response.json()
```

### Codes d'erreur à gérer
| Code | Action |
|------|--------|
| 429 | Backoff exponentiel, réessayer après le délai indiqué |
| 500/503 | Retry 3 fois avec backoff, logger si persistant |
| 401 | Logger + alerte admin (clé API expirée/invalide) |
| 404 | Skin inexistant sur la plateforme, skip |
