'use client';

import Link from 'next/link';
import { RefreshCw } from 'lucide-react';
import { useSkins, useSyncSkins } from '@/hooks/useSkins';
import { StatusBadge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { computePnl, formatEur, formatPercent, formatPnl, pnlClasses } from '@/lib/utils';

export default function SkinsPage() {
  const { data: skins, isLoading } = useSkins();
  const syncMutation = useSyncSkins();

  return (
    <div className="p-6 space-y-4">
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
          Sync inventaire
        </Button>
      </div>

      {syncMutation.isSuccess && (
        <div className="bg-green-900/20 border border-green-800/40 rounded-md px-4 py-2 text-sm text-green-400">
          {syncMutation.data.message}
        </div>
      )}
      {syncMutation.isError && (
        <div className="bg-red-900/20 border border-red-800/40 rounded-md px-4 py-2 text-sm text-red-400">
          {syncMutation.error instanceof Error ? syncMutation.error.message : 'Erreur de synchronisation'}
        </div>
      )}

      {isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-12 bg-zinc-800 animate-pulse rounded-md" />
          ))}
        </div>
      ) : (
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-zinc-800">
                <th className="text-left px-4 py-3 text-xs font-medium text-zinc-500">Skin</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-zinc-500">Statut</th>
                <th className="text-right px-4 py-3 text-xs font-medium text-zinc-500">Prix actuel</th>
                <th className="text-right px-4 py-3 text-xs font-medium text-zinc-500">Prix d'achat</th>
                <th className="text-right px-4 py-3 text-xs font-medium text-zinc-500">P&L</th>
              </tr>
            </thead>
            <tbody>
              {skins?.map((skin) => {
                const { cents, percent } = computePnl(
                  skin.last_price_cents,
                  skin.purchase_price_cents,
                );
                return (
                  <tr
                    key={skin.id}
                    className="border-b border-zinc-800 last:border-0 hover:bg-zinc-800/40 transition-colors"
                  >
                    <td className="px-4 py-3">
                      <Link
                        href={`/skins/${skin.id}`}
                        className="text-sm text-zinc-200 hover:text-indigo-400 transition-colors"
                      >
                        {skin.market_hash_name}
                      </Link>
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={skin.status} />
                    </td>
                    <td className="px-4 py-3 text-right text-sm text-zinc-200">
                      {formatEur(skin.last_price_cents)}
                    </td>
                    <td className="px-4 py-3 text-right text-sm text-zinc-400">
                      {formatEur(skin.purchase_price_cents)}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className={`text-sm font-medium ${pnlClasses(cents)}`}>
                        {formatPnl(cents)}
                      </div>
                      <div className={`text-xs ${pnlClasses(percent)}`}>
                        {formatPercent(percent)}
                      </div>
                    </td>
                  </tr>
                );
              })}
              {skins?.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-4 py-10 text-center text-zinc-600 text-sm">
                    Aucun skin — lance un Sync inventaire pour importer depuis Steam
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
