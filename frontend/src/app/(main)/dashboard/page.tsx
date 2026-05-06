'use client';

import { AlertTriangle, Package, TrendingDown, TrendingUp } from 'lucide-react';
import { usePortfolioHistory, usePortfolioSummary } from '@/hooks/usePortfolio';
import { useSkins } from '@/hooks/useSkins';
import { PortfolioChart } from '@/components/charts/PortfolioChart';
import { StatusBadge } from '@/components/ui/Badge';
import { Card } from '@/components/ui/Card';
import { computePnl, formatEur, formatPercent, formatPnl, pnlClasses } from '@/lib/utils';

export default function DashboardPage() {
  const { data: summary, isLoading } = usePortfolioSummary();
  const { data: history } = usePortfolioHistory();
  const { data: skins } = useSkins();

  const alertSkins = skins?.filter((s) => s.status === 'alert' || s.status === 'reminder') ?? [];

  if (isLoading) {
    return (
      <div className="p-6 space-y-4">
        <div className="h-8 bg-zinc-800 animate-pulse rounded w-40" />
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-24 bg-zinc-800 animate-pulse rounded-lg" />
          ))}
        </div>
      </div>
    );
  }

  const pnlPositive = (summary?.total_pnl_cents ?? 0) >= 0;

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-xl font-bold text-zinc-100">Dashboard</h1>
        <p className="text-zinc-500 text-sm mt-0.5">Vue d'ensemble de votre portefeuille</p>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <div className="flex items-start justify-between">
            <div>
              <p className="text-zinc-500 text-xs">Valeur totale</p>
              <p className="text-2xl font-bold text-zinc-100 mt-1">
                {formatEur(summary?.total_current_value_cents ?? null)}
              </p>
            </div>
            <Package className="w-4 h-4 text-zinc-600 mt-0.5" />
          </div>
        </Card>

        <Card>
          <div className="flex items-start justify-between">
            <div>
              <p className="text-zinc-500 text-xs">P&L total</p>
              <p className={`text-2xl font-bold mt-1 ${pnlClasses(summary?.total_pnl_cents)}`}>
                {formatPnl(summary?.total_pnl_cents ?? null)}
              </p>
            </div>
            {pnlPositive ? (
              <TrendingUp className="w-4 h-4 text-green-500/60 mt-0.5" />
            ) : (
              <TrendingDown className="w-4 h-4 text-red-500/60 mt-0.5" />
            )}
          </div>
        </Card>

        <Card>
          <p className="text-zinc-500 text-xs">P&L %</p>
          <p className={`text-2xl font-bold mt-1 ${pnlClasses(summary?.total_pnl_percent)}`}>
            {formatPercent(summary?.total_pnl_percent ?? null)}
          </p>
        </Card>

        <Card>
          <div className="flex items-start justify-between">
            <div>
              <p className="text-zinc-500 text-xs">Alertes actives</p>
              <p className="text-2xl font-bold text-red-400 mt-1">{alertSkins.length}</p>
            </div>
            <AlertTriangle className="w-4 h-4 text-red-500/60 mt-0.5" />
          </div>
        </Card>
      </div>

      <Card>
        <h2 className="text-xs font-medium text-zinc-500 uppercase tracking-wider mb-4">
          Évolution du portefeuille (30 jours)
        </h2>
        {history && history.length > 0 ? (
          <PortfolioChart data={history} />
        ) : (
          <div className="h-[200px] flex items-center justify-center text-zinc-600 text-sm">
            Aucune donnée de prix disponible
          </div>
        )}
      </Card>

      {alertSkins.length > 0 && (
        <Card>
          <h2 className="text-xs font-medium text-zinc-500 uppercase tracking-wider mb-3">
            Skins en alerte
          </h2>
          <div className="space-y-0">
            {alertSkins.map((skin) => {
              const { cents, percent } = computePnl(skin.last_price_cents, skin.purchase_price_cents);
              return (
                <div
                  key={skin.id}
                  className="flex items-center justify-between py-2.5 border-b border-zinc-800 last:border-0"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <StatusBadge status={skin.status} />
                    <span className="text-sm text-zinc-200 truncate">{skin.market_hash_name}</span>
                  </div>
                  <div className="text-right ml-4 shrink-0">
                    <p className="text-sm font-medium text-zinc-100">
                      {formatEur(skin.last_price_cents)}
                    </p>
                    <p className={`text-xs ${pnlClasses(percent)}`}>
                      {formatPercent(percent)}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        </Card>
      )}
    </div>
  );
}
