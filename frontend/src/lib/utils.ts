import type { SkinStatus } from '@/types';

export function formatEur(cents: number | null | undefined): string {
  if (cents == null) return '—';
  return new Intl.NumberFormat('fr-FR', {
    style: 'currency',
    currency: 'EUR',
    minimumFractionDigits: 2,
  }).format(cents / 100);
}

export function formatPnl(cents: number | null | undefined): string {
  if (cents == null) return '—';
  const sign = cents >= 0 ? '+' : '';
  return `${sign}${formatEur(cents)}`;
}

export function formatPercent(value: number | null | undefined): string {
  if (value == null) return '—';
  const sign = value >= 0 ? '+' : '';
  return `${sign}${(value * 100).toFixed(1)}%`;
}

export function computePnl(
  lastCents: number | null,
  purchaseCents: number | null,
): { cents: number | null; percent: number | null } {
  if (lastCents == null || purchaseCents == null) return { cents: null, percent: null };
  const cents = lastCents - purchaseCents;
  const percent = purchaseCents > 0 ? cents / purchaseCents : null;
  return { cents, percent };
}

export function statusLabel(status: SkinStatus): string {
  const labels: Record<SkinStatus, string> = {
    passive: 'STABLE',
    active: 'EN HAUSSE',
    alert: 'ALERTE',
    reminder: 'RAPPEL',
    sold: 'VENDU',
  };
  return labels[status];
}

export function statusClasses(status: SkinStatus): string {
  const map: Record<SkinStatus, string> = {
    passive: 'text-zinc-400 bg-zinc-800 border-zinc-700',
    active: 'text-yellow-400 bg-yellow-900/30 border-yellow-700/50',
    alert: 'text-red-400 bg-red-900/30 border-red-700/50',
    reminder: 'text-orange-400 bg-orange-900/30 border-orange-700/50',
    sold: 'text-zinc-600 bg-zinc-900 border-zinc-800',
  };
  return map[status];
}

export function pnlClasses(value: number | null | undefined): string {
  if (value == null) return 'text-zinc-400';
  return value >= 0 ? 'text-green-400' : 'text-red-400';
}
