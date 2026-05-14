export type SkinStatus = 'passive' | 'active' | 'alert' | 'reminder' | 'sold';
export type PriceSource = 'csfloat' | 'skinport' | 'steam';

export interface PriceHistoryPoint {
  hour: string;
  avg_price_cents: number;
  avg_price_eur: number;
}

export interface SkinSummary {
  id: string;
  market_hash_name: string;
  asset_id: string | null;
  icon_url: string | null;
  float_value: number | null;
  rarity: string | null;
  status: SkinStatus;
  purchase_price_cents: number | null;
  purchase_price_eur: number | null;
  last_price_cents: number | null;
  last_price_eur: number | null;
  peak_price_cents: number | null;
  peak_price_eur: number | null;
  peak_price_at: string | null;
  created_at: string;
}

export interface SkinDetail extends SkinSummary {
  price_history: PriceHistoryPoint[];
}

export interface SyncResult {
  synced: number;
  new_skins: number;
  backfill_started: boolean;
  backfill_count: number;
}

export interface PortfolioSummary {
  total_current_value_cents: number;
  total_current_value_eur: number;
  total_purchase_value_cents: number | null;
  total_purchase_value_eur: number | null;
  total_pnl_cents: number | null;
  total_pnl_eur: number | null;
  total_pnl_percent: number | null;
  skin_count_by_status: Record<string, number>;
}

export interface PortfolioHistoryPoint {
  day: string;
  value_cents: number;
  value_eur: number;
}

export interface MarketSearchResult {
  market_hash_name: string;
  csfloat_price_cents: number | null;
  csfloat_price_eur: number | null;
  skinport_median_cents: number | null;
  skinport_median_eur: number | null;
  skinport_min_cents: number | null;
  skinport_min_eur: number | null;
  skinport_max_cents: number | null;
  skinport_max_eur: number | null;
  skinport_quantity: number;
}

export interface WatchlistItem {
  id: string;
  market_hash_name: string;
  alert_on_drop: boolean;
  drop_threshold: number | null;
  alert_on_rise: boolean;
  rise_threshold: number | null;
  last_price_cents: number | null;
  last_price_eur: number | null;
  created_at: string;
}

export interface WatchlistCreate {
  market_hash_name: string;
  alert_on_drop?: boolean;
  drop_threshold?: number | null;
  alert_on_rise?: boolean;
  rise_threshold?: number | null;
}

export interface UserSettings {
  id: string;
  email: string;
  steam_id: string | null;
  discord_id: string | null;
  threshold_up: number;
  threshold_down: number;
}

export interface UserSettingsUpdate {
  steam_id?: string | null;
  discord_id?: string | null;
  threshold_up?: number | null;
  threshold_down?: number | null;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  steam_id?: string | null;
}
