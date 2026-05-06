# CLAUDE.md — CS2 Skin Tracker

## Vue d'ensemble
Application de tracking et d'alerte de prix de skins CS2. Bot de surveillance des prix + interface web multi-utilisateurs. Hébergé sur VPS Debian avec nom de domaine.

## Docs de référence
- [`docs/SPEC.md`](docs/SPEC.md) — Cahier des charges complet (fonctionnel)
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — Architecture technique détaillée
- [`docs/DATABASE.md`](docs/DATABASE.md) — Schéma BDD complet
- [`docs/API.md`](docs/API.md) — APIs externes utilisées

---

## Stack technique

### Backend
- **Runtime** : Python 3.12+
- **Framework** : FastAPI avec typing strict (Pydantic v2)
- **BDD** : PostgreSQL 16 + asyncpg + SQLAlchemy 2.0 (async)
- **Migrations** : Alembic
- **Scheduler** : APScheduler 3.x (polling toutes les 5 min)
- **Auth** : Better Auth (Python SDK)
- **HTTP Client** : httpx (async)

### Frontend
- **Framework** : Next.js 14+ (App Router)
- **Langage** : TypeScript strict (`"strict": true` dans tsconfig)
- **Styles** : Tailwind CSS (thème sombre / trading)
- **Graphiques** : Recharts
- **State** : Zustand ou React Query (TanStack Query)
- **Auth** : Better Auth (Next.js SDK)

### Infrastructure
- **OS** : Debian
- **Reverse proxy** : Nginx + Certbot (SSL)
- **Process manager** : PM2 (frontend) + systemd (backend/bot)
- **BDD** : PostgreSQL hébergé sur le même VPS

---

## Structure du projet

```
cs2-skin-tracker/
├── CLAUDE.md                  ← Ce fichier
├── docs/
│   ├── SPEC.md
│   ├── ARCHITECTURE.md
│   ├── DATABASE.md
│   └── API.md
├── backend/
│   ├── app/
│   │   ├── main.py            ← FastAPI app entry point
│   │   ├── config.py          ← Settings (pydantic-settings)
│   │   ├── database.py        ← DB connection + session
│   │   ├── models/            ← SQLAlchemy ORM models
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   ├── skin.py
│   │   │   ├── price_history.py
│   │   │   ├── watchlist.py
│   │   │   └── alert_log.py
│   │   ├── schemas/           ← Pydantic schemas (request/response)
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   ├── skin.py
│   │   │   └── price.py
│   │   ├── routers/           ← FastAPI routers
│   │   │   ├── auth.py
│   │   │   ├── skins.py
│   │   │   ├── market.py
│   │   │   ├── watchlist.py
│   │   │   └── portfolio.py
│   │   ├── services/          ← Business logic
│   │   │   ├── steam.py       ← Steam API + backfill
│   │   │   ├── csfloat.py     ← CSFloat API client
│   │   │   ├── skinport.py    ← Skinport API client
│   │   │   ├── discord.py     ← Discord bot / webhooks
│   │   │   └── alert.py       ← Logique algo alertes
│   │   └── bot/
│   │       ├── scheduler.py   ← APScheduler setup
│   │       └── tasks.py       ← Tâches planifiées
│   ├── migrations/            ← Alembic migrations
│   ├── tests/
│   ├── .env.example
│   ├── requirements.txt
│   └── alembic.ini
└── frontend/
    ├── src/
    │   ├── app/               ← Next.js App Router
    │   │   ├── layout.tsx
    │   │   ├── page.tsx       ← redirect vers /dashboard
    │   │   ├── (auth)/
    │   │   │   └── login/
    │   │   ├── dashboard/
    │   │   ├── skins/
    │   │   │   └── [id]/
    │   │   ├── market/
    │   │   └── settings/
    │   ├── components/
    │   │   ├── ui/            ← Composants génériques
    │   │   ├── charts/        ← Graphiques Recharts
    │   │   ├── skins/         ← Composants métier skins
    │   │   └── layout/        ← Navbar, Sidebar, etc.
    │   ├── lib/
    │   │   ├── api.ts         ← Fetch wrapper vers backend
    │   │   ├── auth.ts        ← Better Auth client
    │   │   └── utils.ts
    │   ├── types/
    │   │   └── index.ts       ← Tous les types TypeScript
    │   └── hooks/             ← Custom React hooks
    ├── public/
    ├── tailwind.config.ts
    ├── tsconfig.json          ← strict: true obligatoire
    └── package.json
```

---

## Règles de développement

### Typage
- **Python** : Type hints sur toutes les fonctions, Pydantic v2 pour tous les schemas, `mypy` compatible
- **TypeScript** : `strict: true`, zéro `any`, interfaces explicites pour tous les objets
- Pas de `// @ts-ignore` sauf cas exceptionnel documenté

### Nommage
- Python : `snake_case` pour variables/fonctions, `PascalCase` pour classes
- TypeScript : `camelCase` pour variables/fonctions, `PascalCase` pour composants/types
- BDD : `snake_case` pour toutes les colonnes et tables
- Constantes : `UPPER_SNAKE_CASE`

### Architecture
- **Separation of concerns** : routers → services → models. Les routers ne touchent jamais la BDD directement
- **Async partout** : toutes les fonctions I/O doivent être `async/await`
- **Gestion d'erreurs** : exceptions typées, jamais de `except Exception` nu sans log
- **Variables d'env** : zéro secret en dur dans le code, tout passe par `.env`

### Git
- Un fichier `.env.example` à jour à chaque nouvelle variable d'env
- Les migrations Alembic sont committées avec le code qui les nécessite

---

## Variables d'environnement requises

```env
# Backend
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/cs2tracker
SECRET_KEY=...
BETTER_AUTH_SECRET=...

# APIs externes
CSFLOAT_API_KEY=...
SKINPORT_CLIENT_ID=...
SKINPORT_CLIENT_SECRET=...
STEAM_API_KEY=...

# Discord
DISCORD_BOT_TOKEN=...

# Frontend
NEXT_PUBLIC_API_URL=https://ton-domaine.com/api
NEXT_PUBLIC_BETTER_AUTH_URL=https://ton-domaine.com
```

---

## Commandes utiles

```bash
# Backend
cd backend
pip install -r requirements.txt
alembic upgrade head          # Appliquer les migrations
uvicorn app.main:app --reload # Dev server

# Frontend
cd frontend
npm install
npm run dev                   # Dev server
npm run build                 # Build production
npm run type-check            # Vérification TypeScript

# BDD
alembic revision --autogenerate -m "description"  # Nouvelle migration
alembic upgrade head                               # Appliquer
alembic downgrade -1                               # Rollback
```
