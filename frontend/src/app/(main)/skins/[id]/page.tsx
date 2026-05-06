'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { ArrowLeft, ExternalLink } from 'lucide-react';
import { useSkin, useSetPurchasePrice } from '@/hooks/useSkins';
import { PriceChart } from '@/components/charts/PriceChart';
import { StatusBadge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { computePnl, formatEur, formatPercent, formatPnl, pnlClasses } from '@/lib/utils';

export default function SkinDetailPage() {
  const params = useParams();
  const id = params.id as string;

  const { data: skin, isLoading } = useSkin(id);
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
    setPriceMutation.mutate(cents, {
      onSuccess: () => setEditing(false),
    });
  }

  if (isLoading) {
    return (
      <div className="p-6 space-y-4">
        <div className="h-8 bg-zinc-800 animate-pulse rounded w-64" />
        <div className="h-56 bg-zinc-800 animate-pulse rounded-lg" />
      </div>
    );
  }

  if (!skin) {
    return (
      <div className="p-6">
        <p className="text-zinc-500 text-sm">Skin introuvable.</p>
      </div>
    );
  }

  const { cents: pnlCents, percent: pnlPercent } = computePnl(
    skin.last_price_cents,
    skin.purchase_price_cents,
  );
  const csfloatUrl = `https://csfloat.com/buy?market_hash_name=${encodeURIComponent(skin.market_hash_name)}`;
  const addedDate = new Date(skin.created_at).toLocaleDateString('fr-FR');

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-start gap-3">
        <Link
          href="/skins"
          className="mt-1 text-zinc-500 hover:text-zinc-300 transition-colors"
          aria-label="Retour"
        >
          <ArrowLeft className="w-4 h-4" />
        </Link>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-3 flex-wrap">
            <h1 className="text-lg font-bold text-zinc-100 truncate">{skin.market_hash_name}</h1>
            <StatusBadge status={skin.status} />
          </div>
          <p className="text-zinc-600 text-xs mt-0.5">Ajouté le {addedDate}</p>
        </div>
        <a
          href={csfloatUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="shrink-0 flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-zinc-400 hover:text-zinc-100 border border-zinc-700 rounded-md hover:bg-zinc-800 transition-colors"
        >
          <ExternalLink className="w-3 h-3" />
          CSFloat
        </a>
      </div>

      <Card>
        <h2 className="text-xs font-medium text-zinc-500 uppercase tracking-wider mb-4">
          Historique des prix
        </h2>
        {skin.price_history.length > 0 ? (
          <PriceChart data={skin.price_history} />
        ) : (
          <div className="h-[240px] flex items-center justify-center text-zinc-600 text-sm">
            Aucune donnée disponible — le bot doit d'abord collecter des prix
          </div>
        )}
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card>
          <h2 className="text-xs font-medium text-zinc-500 uppercase tracking-wider mb-4">
            Analyse P&L
          </h2>
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-xs text-zinc-500">Prix d'achat</span>
              <div className="flex items-center gap-2">
                <span className="text-sm text-zinc-200 font-medium">
                  {formatEur(skin.purchase_price_cents)}
                </span>
                {!editing && (
                  <button
                    onClick={startEditing}
                    className="text-xs text-indigo-400 hover:text-indigo-300 transition-colors"
                  >
                    Modifier
                  </button>
                )}
              </div>
            </div>
            {editing && (
              <form onSubmit={handleSetPrice} className="flex gap-2">
                <Input
                  type="number"
                  step="0.01"
                  min="0"
                  value={priceInput}
                  onChange={(e) => setPriceInput(e.target.value)}
                  placeholder="Ex: 45.00"
                  className="flex-1"
                  autoFocus
                />
                <Button type="submit" size="sm" loading={setPriceMutation.isPending}>
                  OK
                </Button>
                <Button
                  type="button"
                  size="sm"
                  variant="secondary"
                  onClick={() => setEditing(false)}
                >
                  Annuler
                </Button>
              </form>
            )}
            <div className="flex justify-between items-center">
              <span className="text-xs text-zinc-500">Prix actuel</span>
              <span className="text-sm text-zinc-200 font-medium">
                {formatEur(skin.last_price_cents)}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-xs text-zinc-500">Pic historique</span>
              <span className="text-sm text-zinc-200 font-medium">
                {formatEur(skin.peak_price_cents)}
              </span>
            </div>
            <div className="border-t border-zinc-800 pt-3 flex justify-between items-center">
              <span className="text-xs text-zinc-500">Bénéfice potentiel</span>
              <div className="text-right">
                <p className={`text-sm font-bold ${pnlClasses(pnlCents)}`}>
                  {formatPnl(pnlCents)}
                </p>
                <p className={`text-xs ${pnlClasses(pnlPercent)}`}>
                  {formatPercent(pnlPercent)}
                </p>
              </div>
            </div>
          </div>
        </Card>

        <Card>
          <h2 className="text-xs font-medium text-zinc-500 uppercase tracking-wider mb-4">
            Informations
          </h2>
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-xs text-zinc-500">Statut</span>
              <StatusBadge status={skin.status} />
            </div>
            <div className="flex justify-between items-center">
              <span className="text-xs text-zinc-500">Asset ID Steam</span>
              <span className="text-xs text-zinc-400 font-mono">
                {skin.asset_id ?? '—'}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-xs text-zinc-500">Derniers points de données</span>
              <span className="text-xs text-zinc-400">
                {skin.price_history.length > 0
                  ? `${skin.price_history.length} points`
                  : '—'}
              </span>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}
