'use client';

import { useRouter } from 'next/navigation';
import { RefreshCw } from 'lucide-react';
import { useSkins, useSyncSkins } from '@/hooks/useSkins';
import { Button } from '@/components/ui/Button';
import { computePnl, formatEur, formatPercent, formatPnl, pnlClasses, statusLabel } from '@/lib/utils';
import type { SkinStatus, SkinSummary } from '@/types';

const STEAM_IMG = 'https://community.cloudflare.steamstatic.com/economy/image';

const WEAR_RE = /\((Factory New|Minimal Wear|Field-Tested|Well-Worn|Battle-Scarred)\)$/;

function extractWear(name: string): { baseName: string; wear: string | null } {
  const match = WEAR_RE.exec(name);
  if (!match) return { baseName: name, wear: null };
  return { baseName: name.slice(0, match.index).trimEnd(), wear: match[1] };
}

const RARITY_COLOR: Record<string, string> = {
  Rarity_Ancient_Weapon:   'rgba(235, 75,  75,  0.15)',
  Rarity_Legendary_Weapon: 'rgba(136, 71,  255, 0.15)',
  Rarity_Mythical_Weapon:  'rgba(75,  105, 255, 0.15)',
  Rarity_Rare_Weapon:      'rgba(75,  178, 255, 0.15)',
  Rarity_Ancient:          'rgba(235, 75,  75,  0.15)',
  Rarity_Legendary:        'rgba(136, 71,  255, 0.15)',
};
const RARITY_FALLBACK = 'rgba(63, 63, 70, 0.5)';

function skinGradient(rarity: string | null): string {
  const color = (rarity !== null && RARITY_COLOR[rarity]) ? RARITY_COLOR[rarity] : RARITY_FALLBACK;
  return `linear-gradient(135deg, ${color}, rgb(24, 24, 27))`;
}

const STATUS_DOT_CLASS: Record<SkinStatus, string> = {
  passive: 'bg-green-500',
  active: 'bg-yellow-400',
  alert: 'bg-red-500',
  reminder: 'bg-orange-400',
  sold: 'bg-zinc-600',
};

function StatusDot({ status }: { status: SkinStatus }) {
  return (
    <span
      className={`inline-block w-2 h-2 rounded-full shrink-0 mt-1 ${STATUS_DOT_CLASS[status]}`}
      title={statusLabel(status)}
    />
  );
}

function sortSkins(skins: SkinSummary[]): SkinSummary[] {
  return [...skins].sort((a, b) => {
    if (a.last_price_cents === null && b.last_price_cents === null) return 0;
    if (a.last_price_cents === null) return 1;
    if (b.last_price_cents === null) return -1;
    return b.last_price_cents - a.last_price_cents;
  });
}

function SkinCard({ skin }: { skin: SkinSummary }) {
  const router = useRouter();
  const { cents, percent } = computePnl(skin.last_price_cents, skin.purchase_price_cents);
  const hasPnl = cents !== null;
  const imgUrl = skin.icon_url ? `${STEAM_IMG}/${skin.icon_url}` : null;
  const { baseName, wear } = extractWear(skin.market_hash_name);

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={() => router.push(`/skins/${skin.id}`)}
      onKeyDown={(e) => e.key === 'Enter' && router.push(`/skins/${skin.id}`)}
      className="bg-zinc-900 border border-zinc-800 rounded-lg overflow-hidden cursor-pointer hover:border-zinc-600 transition-all duration-150 group"
    >
      <div
        className="h-24 flex items-center justify-center p-3"
        style={{ background: skinGradient(skin.rarity) }}
      >
        {imgUrl ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={imgUrl}
            alt={skin.market_hash_name}
            className="h-full w-full object-contain group-hover:scale-105 transition-transform duration-150"
          />
        ) : (
          <div className="w-10 h-10 bg-zinc-800 rounded-md" />
        )}
      </div>

      <div className="px-3 py-2 space-y-1.5">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <p className="text-xs font-medium text-zinc-100 leading-tight line-clamp-2">
              {baseName}
            </p>
            {wear !== null && (
              <p className="text-xs text-zinc-500 mt-0.5">{wear}</p>
            )}
            {skin.float_value !== null && (
              <p className="text-xs text-zinc-500 mt-0.5">
                Float : <span className="text-zinc-400">{skin.float_value.toFixed(6)}</span>
              </p>
            )}
          </div>
          <StatusDot status={skin.status} />
        </div>

        <div className="flex items-end justify-between">
          <p className="text-sm font-semibold text-zinc-100">
            {formatEur(skin.last_price_cents)}
          </p>
          {hasPnl && (
            <div className="text-right">
              <p className={`text-xs font-medium ${pnlClasses(cents)}`}>
                {formatPnl(cents)}
              </p>
              <p className={`text-xs ${pnlClasses(percent)}`}>
                {formatPercent(percent)}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function SkeletonCard() {
  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-lg overflow-hidden">
      <div className="h-24 bg-zinc-800 animate-pulse" />
      <div className="px-3 py-2 space-y-1.5">
        <div className="h-3 bg-zinc-800 animate-pulse rounded w-3/4" />
        <div className="h-3 bg-zinc-800 animate-pulse rounded w-1/3" />
        <div className="h-4 bg-zinc-800 animate-pulse rounded w-1/2" />
      </div>
    </div>
  );
}

export default function SkinsPage() {
  const { data: skins, isLoading } = useSkins();
  const syncMutation = useSyncSkins();
  const sorted = skins ? sortSkins(skins) : [];

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-zinc-100">Mes Skins</h1>
          <p className="text-zinc-500 text-sm mt-0.5">
            {skins != null ? `${skins.length} skin${skins.length !== 1 ? 's' : ''}` : '—'}
          </p>
        </div>
        <Button
          variant="secondary"
          size="sm"
          onClick={() => syncMutation.mutate()}
          loading={syncMutation.isPending}
        >
          <RefreshCw className="w-3.5 h-3.5" />
          Sync
        </Button>
      </div>

      {syncMutation.isSuccess && (
        <div className="bg-green-900/20 border border-green-800/40 rounded-md px-4 py-2 text-sm text-green-400">
          {syncMutation.data.message}
        </div>
      )}
      {syncMutation.isError && (
        <div className="bg-red-900/20 border border-red-800/40 rounded-md px-4 py-2 text-sm text-red-400">
          {syncMutation.error instanceof Error
            ? syncMutation.error.message
            : 'Erreur de synchronisation'}
        </div>
      )}

      {isLoading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
      ) : sorted.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-24 text-center">
          <p className="text-zinc-500 text-sm">Aucun skin</p>
          <p className="text-zinc-600 text-xs mt-1">
            Lance un Sync pour importer ton inventaire Steam
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {sorted.map((skin) => (
            <SkinCard key={skin.id} skin={skin} />
          ))}
        </div>
      )}
    </div>
  );
}
