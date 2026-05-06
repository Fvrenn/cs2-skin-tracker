# DATABASE.md — Schéma PostgreSQL

## Conventions
- Toutes les tables en `snake_case`
- Toutes les colonnes en `snake_case`
- Clés primaires : `id` UUID (sauf mention contraire)
- Timestamps : `created_at` et `updated_at` sur toutes les tables
- Prix stockés en **centimes** (integer) pour éviter les flottants
- Pourcentages stockés en **décimal** (ex: 0.25 = 25%)

---

## Tables

### `users`
```sql
CREATE TABLE users (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email         VARCHAR(255) UNIQUE NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  steam_id      VARCHAR(50),           -- SteamID64 de l'utilisateur
  discord_id    VARCHAR(50),           -- ID Discord pour les MP
  -- Seuils d'alerte personnalisés
  threshold_up    DECIMAL(5,4) NOT NULL DEFAULT 0.25,  -- 25% hausse
  threshold_down  DECIMAL(5,4) NOT NULL DEFAULT 0.10,  -- 10% retournement
  -- Timestamps
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### `skins`
Skins possédés par un user (importés depuis l'inventaire Steam).

```sql
CREATE TYPE skin_status AS ENUM ('passive', 'active', 'alert', 'reminder', 'sold');

CREATE TABLE skins (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id           UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  market_hash_name  VARCHAR(255) NOT NULL,  -- ex: "AK-47 | Redline (Field-Tested)"
  asset_id          VARCHAR(50),            -- Steam asset ID
  -- Prix
  purchase_price    INTEGER,               -- Prix d'achat en centimes (saisi manuellement)
  peak_price        INTEGER,               -- Prix le plus haut observé en centimes
  peak_price_at     TIMESTAMPTZ,           -- Date du pic
  -- Statut machine à états
  status            skin_status NOT NULL DEFAULT 'passive',
  -- Vente
  sold_at           TIMESTAMPTZ,
  sold_price        INTEGER,               -- Prix de vente estimé (dernier prix connu)
  -- Timestamps
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  -- Contrainte : un user ne peut pas avoir deux fois le même asset
  UNIQUE(user_id, asset_id)
);

CREATE INDEX idx_skins_user_id ON skins(user_id);
CREATE INDEX idx_skins_market_hash_name ON skins(market_hash_name);
CREATE INDEX idx_skins_status ON skins(status);
```

### `price_history`
Historique de tous les prix collectés (toutes les 5 min + backfill Steam).

```sql
CREATE TYPE price_source AS ENUM ('csfloat', 'skinport', 'steam');

CREATE TABLE price_history (
  id                BIGSERIAL PRIMARY KEY,
  market_hash_name  VARCHAR(255) NOT NULL,
  source            price_source NOT NULL,
  -- Prix en centimes
  price_median      INTEGER,
  price_min         INTEGER,
  price_max         INTEGER,
  price_mean        INTEGER,
  -- Volume de transactions
  volume            INTEGER,
  -- Timestamp de la donnée (pas d'insertion)
  recorded_at       TIMESTAMPTZ NOT NULL,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index composé pour les requêtes fréquentes (graphiques, algo)
CREATE INDEX idx_price_history_lookup
  ON price_history(market_hash_name, source, recorded_at DESC);

-- Pas de doublons pour la même source au même instant
CREATE UNIQUE INDEX idx_price_history_unique
  ON price_history(market_hash_name, source, recorded_at);
```

### `watchlist`
Skins surveillés mais non possédés par l'user.

```sql
CREATE TABLE watchlist (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id           UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  market_hash_name  VARCHAR(255) NOT NULL,
  -- Alertes configurées
  alert_on_drop     BOOLEAN NOT NULL DEFAULT FALSE,
  drop_threshold    DECIMAL(5,4),    -- ex: 0.15 = alerte si baisse de 15%
  alert_on_rise     BOOLEAN NOT NULL DEFAULT FALSE,
  rise_threshold    DECIMAL(5,4),    -- ex: 0.20 = alerte si hausse de 20%
  -- Timestamps
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(user_id, market_hash_name)
);

CREATE INDEX idx_watchlist_user_id ON watchlist(user_id);
```

### `alert_logs`
Log de toutes les alertes envoyées (pour éviter le spam et garder l'historique).

```sql
CREATE TYPE alert_type AS ENUM (
  'rise',       -- Skin a atteint le seuil de hausse
  'peak_drop',  -- Retournement détecté depuis le pic
  'reminder',   -- Rappel baisse continue
  'watchlist_drop',  -- Watchlist : prix a baissé
  'watchlist_rise'   -- Watchlist : prix a monté
);

CREATE TABLE alert_logs (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  skin_id     UUID REFERENCES skins(id) ON DELETE SET NULL,  -- null si watchlist
  watchlist_id UUID REFERENCES watchlist(id) ON DELETE SET NULL,
  alert_type  alert_type NOT NULL,
  -- Snapshot des données au moment de l'alerte
  price_at_alert    INTEGER NOT NULL,   -- Prix en centimes au moment de l'alerte
  peak_price_ref    INTEGER,            -- Prix du pic de référence
  purchase_price_ref INTEGER,           -- Prix d'achat de référence
  -- Message envoyé
  discord_message   TEXT,
  discord_sent      BOOLEAN NOT NULL DEFAULT FALSE,
  sent_at           TIMESTAMPTZ,
  -- Timestamps
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_alert_logs_user_id ON alert_logs(user_id);
CREATE INDEX idx_alert_logs_skin_id ON alert_logs(skin_id);
CREATE INDEX idx_alert_logs_created_at ON alert_logs(created_at DESC);
```

---

## Requêtes clés

### Dernier prix connu d'un skin
```sql
SELECT price_median, recorded_at
FROM price_history
WHERE market_hash_name = $1 AND source = 'csfloat'
ORDER BY recorded_at DESC
LIMIT 1;
```

### Historique 30 derniers jours (pour graphique)
```sql
SELECT
  DATE_TRUNC('hour', recorded_at) AS hour,
  AVG(price_median) AS avg_price,
  MIN(price_min) AS min_price,
  MAX(price_max) AS max_price
FROM price_history
WHERE
  market_hash_name = $1
  AND source = 'csfloat'
  AND recorded_at > NOW() - INTERVAL '30 days'
GROUP BY 1
ORDER BY 1;
```

### Valeur totale du portefeuille d'un user
```sql
SELECT
  SUM(ph.price_median) AS total_current_value,
  SUM(s.purchase_price) AS total_purchase_value,
  SUM(ph.price_median - s.purchase_price) AS total_pnl
FROM skins s
JOIN LATERAL (
  SELECT price_median
  FROM price_history
  WHERE market_hash_name = s.market_hash_name AND source = 'csfloat'
  ORDER BY recorded_at DESC
  LIMIT 1
) ph ON TRUE
WHERE s.user_id = $1 AND s.status != 'sold';
```

### Évolution du portefeuille dans le temps (par jour)
```sql
SELECT
  DATE_TRUNC('day', ph.recorded_at) AS day,
  SUM(ph.price_median) AS portfolio_value
FROM skins s
JOIN price_history ph ON ph.market_hash_name = s.market_hash_name
  AND ph.source = 'csfloat'
WHERE s.user_id = $1 AND s.status != 'sold'
GROUP BY 1
ORDER BY 1;
```

### Dernière alerte envoyée pour un skin (anti-spam)
```sql
SELECT created_at
FROM alert_logs
WHERE skin_id = $1 AND alert_type = $2
ORDER BY created_at DESC
LIMIT 1;
```

---

## Notes importantes
- Les prix sont **toujours en centimes** dans la BDD. Diviser par 100 pour l'affichage.
- `recorded_at` dans `price_history` est la date réelle de la donnée (pas d'insertion en BDD).
- Pour le backfill Steam, `recorded_at` correspond à la date historique du prix.
- Les `alert_logs` ne sont jamais supprimés — c'est l'historique complet des notifications.
