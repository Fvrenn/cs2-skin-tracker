import { getToken, removeToken } from '@/lib/auth';
import type {
  MarketSearchResult,
  PortfolioHistoryPoint,
  PortfolioSummary,
  SkinDetail,
  SkinSummary,
  SyncResult,
  TokenResponse,
  UserSettings,
  UserSettingsUpdate,
  WatchlistCreate,
  WatchlistItem,
} from '@/types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const token = getToken();

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token != null ? { Authorization: `Bearer ${token}` } : {}),
      ...options?.headers,
    },
  });

  if (res.status === 401) {
    removeToken();
    if (typeof window !== 'undefined') {
      window.location.replace('/login');
    }
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText })) as { detail?: string };
    throw new Error(body.detail ?? `HTTP ${res.status}`);
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  auth: {
    login: (email: string, password: string) =>
      apiFetch<TokenResponse>('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      }),
    register: (email: string, password: string, steamId?: string) =>
      apiFetch<TokenResponse>('/auth/register', {
        method: 'POST',
        body: JSON.stringify({ email, password, steam_id: steamId ?? null }),
      }),
    logout: () =>
      apiFetch<void>('/auth/logout', { method: 'POST' }),
  },
  skins: {
    list: () => apiFetch<SkinSummary[]>('/skins'),
    get: (id: string, days = 30) =>
      apiFetch<SkinDetail>(`/skins/${id}?days=${days}`),
    setPurchasePrice: (id: string, priceCents: number) =>
      apiFetch<SkinSummary>(`/skins/${id}/purchase-price`, {
        method: 'POST',
        body: JSON.stringify({ purchase_price: priceCents }),
      }),
    sync: () => apiFetch<SyncResult>('/skins/sync', { method: 'POST' }),
  },
  portfolio: {
    summary: () => apiFetch<PortfolioSummary>('/portfolio/summary'),
    history: () => apiFetch<PortfolioHistoryPoint[]>('/portfolio/history'),
  },
  market: {
    search: (q: string) =>
      apiFetch<MarketSearchResult>(`/market/search?q=${encodeURIComponent(q)}`),
  },
  watchlist: {
    list: () => apiFetch<WatchlistItem[]>('/watchlist'),
    add: (item: WatchlistCreate) =>
      apiFetch<WatchlistItem>('/watchlist', {
        method: 'POST',
        body: JSON.stringify(item),
      }),
    remove: (id: string) =>
      apiFetch<void>(`/watchlist/${id}`, { method: 'DELETE' }),
  },
  settings: {
    get: () => apiFetch<UserSettings>('/settings'),
    update: (data: UserSettingsUpdate) =>
      apiFetch<UserSettings>('/settings', {
        method: 'PUT',
        body: JSON.stringify(data),
      }),
  },
};
