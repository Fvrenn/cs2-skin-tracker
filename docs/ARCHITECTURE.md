# ARCHITECTURE.md — Architecture technique

## Vue d'ensemble

```
┌─────────────────────────────────────────────────────┐
│                      VPS Debian                      │
│                                                     │
│  ┌──────────┐    ┌──────────────┐    ┌───────────┐  │
│  │ Next.js  │───▶│   Nginx      │◀───│  FastAPI  │  │
│  │ :3000    │    │   :443       │    │  :8000    │  │
│  └──────────┘    └──────────────┘    └─────┬─────┘  │
│                                            │        │
│  ┌─────────────────────────┐    ┌──────────▼──────┐  │
│  │     Bot / Scheduler     │───▶│   PostgreSQL    │  │
│  │  APScheduler (5 min)    │    │   :5432         │  │
│  └────────────┬────────────┘    └─────────────────┘  │
│               │                                     │
└───────────────┼─────────────────────────────────────┘
                │
        ┌───────▼────────┐
        │  APIs externes  │
        │  - CSFloat      │
        │  - Skinport     │
        │  - Steam API    │
        │  - Discord API  │
        └────────────────┘
```

---

## Backend — FastAPI

### Principes
- **Async/await partout** : toutes les opérations I/O sont non-bloquantes
- **Dependency injection** : session BDD, user authentifié injectés via `Depends()`
- **Pydantic v2** : validation stricte sur tous les inputs/outputs
- **Séparation routers / services / models** : les routers orchestrent, les services contiennent la logique

### Routers

| Router | Préfixe | Responsabilité |
|--------|---------|----------------|
| `auth.py` | `/auth` | Login, logout, session (Better Auth) |
| `skins.py` | `/skins` | CRUD skins, import inventaire, prix d'achat |
| `market.py` | `/market` | Explorer le marché CSFloat/Skinport |
| `watchlist.py` | `/watchlist` | Gestion de la watchlist |
| `portfolio.py` | `/portfolio` | P&L, historique valeur totale |

### Services

| Service | Responsabilité |
|---------|----------------|
| `steam.py` | Import inventaire Steam, backfill historique prix |
| `csfloat.py` | Client API CSFloat (listings, prix) |
| `skinport.py` | Client API Skinport (items, history) |
| `discord.py` | Envoi de MP Discord via bot |
| `alert.py` | Machine à états, détection des signaux |

### Bot / Scheduler

```python
# Tâches planifiées (APScheduler)

@scheduler.scheduled_job('interval', minutes=5)
async def poll_prices():
    """
    Fetch les prix de tous les skins actifs sur CSFloat + Skinport.
    Stocke en price_history.
    Lance la machine à états pour chaque skin de chaque user.
    Vérifie les inventaires Steam pour détecter les ventes.
    Vérifie les watchlists.
    """

@scheduler.scheduled_job('cron', hour=2)  # 2h du matin
async def backfill_missing():
    """
    Complète les éventuels trous dans l'historique Steam.
    """
```

---

## Frontend — Next.js

### App Router structure

```
app/
├── layout.tsx              ← Layout global (navbar, sidebar, theme)
├── page.tsx                ← Redirect → /dashboard
├── (auth)/
│   └── login/
│       └── page.tsx        ← Page login
├── dashboard/
│   └── page.tsx            ← Dashboard principal
├── skins/
│   ├── page.tsx            ← Liste des skins
│   └── [id]/
│       └── page.tsx        ← Détail d'un skin
├── market/
│   └── page.tsx            ← Explorer le marché
└── settings/
    └── page.tsx            ← Paramètres user
```

### Conventions composants
- **Server Components** par défaut (Next.js App Router)
- **Client Components** (`'use client'`) uniquement si interactivité nécessaire
- **Nommage** : `PascalCase` pour les composants, fichiers en `kebab-case`
- **Props typées** : interface explicite pour chaque composant

```typescript
// ✅ Bon
interface SkinCardProps {
  skin: Skin;
  currentPrice: number;
  onRefresh: () => void;
}

export function SkinCard({ skin, currentPrice, onRefresh }: SkinCardProps) { ... }

// ❌ Mauvais
export function SkinCard({ skin, currentPrice, onRefresh }: any) { ... }
```

### Types globaux (`src/types/index.ts`)

```typescript
export type SkinStatus = 'passive' | 'active' | 'alert' | 'reminder' | 'sold';
export type PriceSource = 'csfloat' | 'skinport' | 'steam';
export type AlertType = 'rise' | 'peak_drop' | 'reminder' | 'watchlist_drop' | 'watchlist_rise';

export interface User {
  id: string;
  email: string;
  steamId: string | null;
  discordId: string | null;
  thresholdUp: number;
  thresholdDown: number;
}

export interface Skin {
  id: string;
  marketHashName: string;
  assetId: string | null;
  purchasePrice: number | null;  // en centimes
  peakPrice: number | null;      // en centimes
  peakPriceAt: string | null;
  status: SkinStatus;
  soldAt: string | null;
  createdAt: string;
}

export interface PricePoint {
  recordedAt: string;
  priceMedian: number;  // en centimes
  priceMin: number | null;
  priceMax: number | null;
  volume: number | null;
}

export interface Portfolio {
  totalCurrentValue: number;   // en centimes
  totalPurchaseValue: number;  // en centimes
  totalPnl: number;            // en centimes
  totalPnlPercent: number;     // ex: 0.25 = +25%
}
```

---

## APIs externes

### CSFloat
- **Base URL** : `https://csfloat.com/api/v1`
- **Auth** : Header `Authorization: <API-KEY>`
- **Usage** : Fetch listings par `market_hash_name`, prix live
- **Rate limit** : Non documenté → 1 requête / 6 secondes conseillé
- **Prix** : En centimes (diviser par 100)

### Skinport
- **Base URL** : `https://api.skinport.com/v1`
- **Auth** : Basic Auth (`clientId:clientSecret` en base64) — endpoints publics sans auth
- **Usage** : `/items` (prix live), `/sales/history` (stats 24h/7j/30j/90j)
- **Cache** : 5 minutes côté serveur — inutile d'appeler plus souvent
- **Rate limit** : 8 req / 5 min sur les endpoints principaux
- **Encoding** : Header `Accept-Encoding: br` obligatoire

### Steam Market
- **Base URL** : `https://steamcommunity.com/market`
- **Endpoints** :
  - `/pricehistory/?appid=730&market_hash_name=...` → historique long terme
  - `https://steamcommunity.com/inventory/<steamid>/730/2` → inventaire
- **Auth** : Cookie `steamLoginSecure` pour pricehistory, inventaire public si paramètre public
- **Rate limit** : strict — espacer les requêtes de backfill (1 req / 3 sec minimum)

### Discord Bot
- Créer un bot Discord sur https://discord.com/developers/applications
- Permission nécessaire : `Send Messages` dans les DMs
- L'user doit avoir son `discord_id` renseigné dans ses settings
- Le bot doit partager un serveur commun avec l'user pour envoyer des DMs

---

## Infrastructure VPS

### Nginx config (simplifié)
```nginx
# Frontend Next.js
server {
    listen 443 ssl;
    server_name ton-domaine.com;

    location / {
        proxy_pass http://localhost:3000;
    }

    location /api/ {
        proxy_pass http://localhost:8000/;
    }
}
```

### Process management
```bash
# Backend FastAPI (systemd)
# /etc/systemd/system/cs2tracker-api.service

# Bot scheduler (systemd)
# /etc/systemd/system/cs2tracker-bot.service

# Frontend Next.js (PM2)
pm2 start npm --name "cs2tracker-frontend" -- start
```

### Variables d'environnement
- Fichier `/etc/cs2tracker/.env` sur le VPS (hors du repo Git)
- Chargé par systemd via `EnvironmentFile=`
- `.env.example` committé dans le repo avec toutes les clés (valeurs vides)

---

## Sécurité

- HTTPS obligatoire (Certbot + Let's Encrypt)
- API Key CSFloat uniquement côté backend (jamais exposée au frontend)
- PostgreSQL accessible uniquement en local (`localhost`) — pas d'exposition externe
- Better Auth gère les sessions avec JWT sécurisés (httpOnly cookies)
- Rate limiting Nginx sur les endpoints `/api/` pour éviter les abus
