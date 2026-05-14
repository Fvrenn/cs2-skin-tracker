'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { ArrowLeft, Check, ExternalLink, Pencil, X } from 'lucide-react';
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { useSkin, useSetPurchasePrice } from '@/hooks/useSkins';
import { StatusBadge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { computePnl, formatEur, formatPercent, formatPnl, pnlClasses } from '@/lib/utils';

const STEAM_IMG = 'https://community.cloudflare.steamstatic.com/economy/image';

const RARITY_COLOR: Record<string, string> = {
  Rarity_Ancient_Weapon:   'rgba(235, 75,  75,  0.15)',
  Rarity_Legendary_Weapon: 'rgba(136, 71,  255, 0.15)',
  Rarity_Mythical_Weapon:  'rgba(75,  105, 255, 0.15)',
  Rarity_Rare_Weapon:      'rgba(75,  178, 255, 0.15)',
  Rarity_Ancient:          'rgba(235, 75,  75,  0.15)',
  Rarity_Legendary:        'rgba(136, 71,  255, 0.15)',
};

function skinGradient(rarity: string | null): string {
  const color = rarity !== null && RARITY_COLOR[rarity]
    ? RARITY_COLOR[rarity]
    : 'rgba(63, 63, 70, 0.5)';
  return `linear-gradient(135deg, ${color}, rgb(24, 24, 27))`;
}

const WEAR_RE = /\((Factory New|Minimal Wear|Field-Tested|Well-Worn|Battle-Scarred)\)$/;

function extractWear(name: string): { baseName: string; wear: string | null } {
  const match = WEAR_RE.exec(name);
  if (!match) return { baseName: name, wear: null };
  return { baseName: name.slice(0, match.index).trimEnd(), wear: match[1] };
}

const PERIODS = [
  { label: '7j',   days: 7    },
  { label: '30j',  days: 30   },
  { label: '90j',  days: 90   },
  { label: '1an',  days: 365  },
  { label: 'Tout', days: 3650 },
] as const;

type PeriodDays = (typeof PERIODS)[number]['days'];

interface ChartPoint {
  date: string;
  price: number;
}

function SkinPriceChart({
  data,
  lineColor,
  purchasePriceCents,
}: {
  data: ChartPoint[];
  lineColor: string;
  purchasePriceCents: number | null;
}) {
  const purchasePriceEur =
    purchasePriceCents !== null ? purchasePriceCents / 100 : null;

  return (
    <ResponsiveContainer width="100%" height={240}>
      <LineChart data={data} margin={{ top: 5, right: 10, bottom: 5, left: 10 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
        <XAxis
          dataKey="date"
          tick={{ fontSize: 11, fill: '#71717a' }}
          axisLine={false}
          tickLine={false}
          interval="preserveStartEnd"
          tickFormatter={(v: string) =>
            new Date(v).toLocaleDateString('fr-FR', {
              day: '2-digit',
              month: '2-digit',
            })
          }
        />
        <YAxis
          tick={{ fontSize: 11, fill: '#71717a' }}
          axisLine={false}
          tickLine={false}
          tickFormatter={(v: number) => `${v.toFixed(0)} €`}
          width={52}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: '#18181b',
            border: '1px solid #3f3f46',
            borderRadius: '6px',
            fontSize: 12,
          }}
          labelStyle={{ color: '#71717a', marginBottom: 4 }}
          itemStyle={{ color: lineColor }}
          labelFormatter={(label: string) =>
            new Date(label).toLocaleDateString('fr-FR', {
              day: '2-digit',
              month: 'long',
              year: 'numeric',
            })
          }
          formatter={(value: number) => [`${value.toFixed(2)} €`, 'Prix']}
        />
        {purchasePriceEur !== null && (
          <ReferenceLine
            y={purchasePriceEur}
            stroke="#52525b"
            strokeDasharray="4 4"
            label={{
              value: `Achat ${purchasePriceEur.toFixed(2)} €`,
              fill: '#71717a',
              fontSize: 10,
              position: 'insideTopRight',
            }}
          />
        )}
        <Line
          type="monotone"
          dataKey="price"
          stroke={lineColor}
          strokeWidth={2}
          dot={false}
          activeDot={{ r: 4, fill: lineColor }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}

function MetricCard({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
      <p className="text-xs text-zinc-500 uppercase tracking-wider mb-2">{label}</p>
      {children}
    </div>
  );
}

export default function SkinDetailPage() {
  const params = useParams();
  const id = params.id as string;

  const [selectedDays, setSelectedDays] = useState<PeriodDays>(30);
  const { data: skin, isLoading } = useSkin(id, selectedDays);
  const setPriceMutation = useSetPurchasePrice(id);

  const [editing, setEditing] = useState(false);
  const [priceInput, setPriceInput] = useState('');

  function startEditing() {
    setPriceInput(
      skin?.purchase_price_cents != null
        ? (skin.purchase_price_cents / 100).toFixed(2)
        : '',
    );
    setEditing(true);
  }

  function handleSetPrice(e: React.FormEvent) {
    e.preventDefault();
    const cents = Math.round(parseFloat(priceInput) * 100);
    if (!isFinite(cents) || cents < 0) return;
    setPriceMutation.mutate(cents, { onSuccess: () => setEditing(false) });
  }

  if (isLoading && skin == null) {
    return (
      <div className="p-6 space-y-5">
        <div className="h-4 bg-zinc-800 animate-pulse rounded w-24" />
        <div className="h-36 bg-zinc-800 animate-pulse rounded-lg" />
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-20 bg-zinc-800 animate-pulse rounded-lg" />
          ))}
        </div>
        <div className="h-72 bg-zinc-800 animate-pulse rounded-lg" />
      </div>
    );
  }

  if (skin == null) {
    return (
      <div className="p-6">
        <p className="text-zinc-500 text-sm">Skin introuvable.</p>
      </div>
    );
  }

  const { baseName, wear } = extractWear(skin.market_hash_name);
  const { cents: pnlCents, percent: pnlPercent } = computePnl(
    skin.last_price_cents,
    skin.purchase_price_cents,
  );

  const csfloatUrl = `https://csfloat.com/market?search=${encodeURIComponent(skin.market_hash_name)}`;
  const addedDate = new Date(skin.created_at).toLocaleDateString('fr-FR');
  const peakDate =
    skin.peak_price_at != null
      ? new Date(skin.peak_price_at).toLocaleDateString('fr-FR', {
          day: '2-digit',
          month: 'short',
          year: 'numeric',
        })
      : null;

  const chartData: ChartPoint[] = skin.price_history.map((p) => ({
    date: p.hour,
    price: p.avg_price_cents / 100,
  }));
  const firstPrice = chartData.at(0)?.price ?? null;
  const lastPrice = chartData.at(-1)?.price ?? null;
  const lineColor =
    firstPrice !== null && lastPrice !== null && lastPrice >= firstPrice
      ? '#22c55e'
      : '#ef4444';

  return (
    <div className="p-6 space-y-5">
      <Link
        href="/skins"
        className="inline-flex items-center gap-1.5 text-xs text-zinc-500 hover:text-zinc-300 transition-colors"
      >
        <ArrowLeft className="w-3.5 h-3.5" />
        Mes Skins
      </Link>

      {/* Header */}
      <div
        className="rounded-lg border border-zinc-800 overflow-hidden"
        style={{ background: skinGradient(skin.rarity) }}
      >
        <div className="p-5 flex gap-5 items-center">
          <div className="shrink-0 w-28 h-28 flex items-center justify-center">
            {skin.icon_url ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={`${STEAM_IMG}/${skin.icon_url}`}
                alt={skin.market_hash_name}
                className="w-full h-full object-contain"
              />
            ) : (
              <div className="w-16 h-16 bg-zinc-800 rounded-md" />
            )}
          </div>

          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-3 flex-wrap">
              <h1 className="text-xl font-bold text-zinc-100 leading-tight">
                {baseName}
              </h1>
              <StatusBadge status={skin.status} />
            </div>
            {wear !== null && (
              <p className="text-sm text-zinc-400 mt-1">{wear}</p>
            )}
            {skin.float_value !== null && (
              <p className="text-xs text-zinc-500 mt-0.5">
                Float : {skin.float_value.toFixed(6)}
              </p>
            )}
            <p className="text-xs text-zinc-600 mt-2">Ajouté le {addedDate}</p>
          </div>

          <a
            href={csfloatUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="shrink-0 flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-zinc-300 bg-zinc-800/60 hover:bg-zinc-700/60 border border-zinc-700 rounded-md transition-colors"
          >
            <ExternalLink className="w-3.5 h-3.5" />
            Voir sur CSFloat
          </a>
        </div>
      </div>

      {/* 4 metric cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <MetricCard label="Prix d'achat">
          {editing ? (
            <form onSubmit={handleSetPrice} className="flex gap-1 mt-1">
              <Input
                type="number"
                step="0.01"
                min="0"
                value={priceInput}
                onChange={(e) => setPriceInput(e.target.value)}
                placeholder="45.00"
                autoFocus
              />
              <Button type="submit" size="sm" loading={setPriceMutation.isPending}>
                <Check className="w-3.5 h-3.5" />
              </Button>
              <Button
                type="button"
                size="sm"
                variant="secondary"
                onClick={() => setEditing(false)}
              >
                <X className="w-3.5 h-3.5" />
              </Button>
            </form>
          ) : (
            <button
              onClick={startEditing}
              className="group flex items-center gap-2 text-left"
            >
              <span className="text-xl font-bold text-zinc-100">
                {formatEur(skin.purchase_price_cents)}
              </span>
              <Pencil className="w-3 h-3 text-zinc-600 group-hover:text-zinc-400 transition-colors" />
            </button>
          )}
        </MetricCard>

        <MetricCard label="Prix actuel">
          <p className="text-xl font-bold text-zinc-100">
            {formatEur(skin.last_price_cents)}
          </p>
        </MetricCard>

        <MetricCard label="Pic historique">
          <p className="text-xl font-bold text-zinc-100">
            {formatEur(skin.peak_price_cents)}
          </p>
          {peakDate !== null && (
            <p className="text-xs text-zinc-500 mt-0.5">{peakDate}</p>
          )}
        </MetricCard>

        <MetricCard label="P&L">
          <p className={`text-xl font-bold ${pnlClasses(pnlCents)}`}>
            {formatPnl(pnlCents)}
          </p>
          <p className={`text-xs mt-0.5 ${pnlClasses(pnlPercent)}`}>
            {formatPercent(pnlPercent)}
          </p>
        </MetricCard>
      </div>

      {/* Chart */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
        <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
          <h2 className="text-xs font-medium text-zinc-500 uppercase tracking-wider">
            Historique des prix
          </h2>
          <div className="flex gap-1">
            {PERIODS.map((p) => (
              <button
                key={p.days}
                onClick={() => setSelectedDays(p.days)}
                className={`px-2.5 py-1 text-xs rounded transition-colors ${
                  selectedDays === p.days
                    ? 'bg-indigo-500/20 text-indigo-400 border border-indigo-500/30'
                    : 'text-zinc-500 hover:text-zinc-300 border border-transparent'
                }`}
              >
                {p.label}
              </button>
            ))}
          </div>
        </div>

        {chartData.length > 0 ? (
          <SkinPriceChart
            data={chartData}
            lineColor={lineColor}
            purchasePriceCents={skin.purchase_price_cents}
          />
        ) : (
          <div className="h-60 flex items-center justify-center text-zinc-600 text-sm">
            Aucune donnée sur cette période
          </div>
        )}
      </div>

      {/* Alerts */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
        <h2 className="text-xs font-medium text-zinc-500 uppercase tracking-wider mb-3">
          Alertes
        </h2>
        <p className="text-xs text-zinc-600">Aucune alerte pour ce skin</p>
      </div>
    </div>
  );
}
