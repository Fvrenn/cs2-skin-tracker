'use client';

import { useState } from 'react';
import { Plus, Search } from 'lucide-react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { formatEur } from '@/lib/utils';
import type { WatchlistCreate } from '@/types';

export default function MarketPage() {
  const [query, setQuery] = useState('');
  const [submitted, setSubmitted] = useState('');
  const queryClient = useQueryClient();

  const {
    data: result,
    isLoading,
    error,
    isFetching,
  } = useQuery({
    queryKey: ['market', 'search', submitted],
    queryFn: () => api.market.search(submitted),
    enabled: submitted.length > 0,
    retry: false,
  });

  const addToWatchlist = useMutation({
    mutationFn: (item: WatchlistCreate) => api.watchlist.add(item),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['watchlist'] });
    },
  });

  function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = query.trim();
    if (trimmed) setSubmitted(trimmed);
  }

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-xl font-bold text-zinc-100">Marché</h1>
        <p className="text-zinc-500 text-sm mt-0.5">
          Recherche par market_hash_name exact (ex: AK-47 | Redline (Field-Tested))
        </p>
      </div>

      <form onSubmit={handleSearch} className="flex gap-3">
        <div className="flex-1">
          <Input
            placeholder="AK-47 | Redline (Field-Tested)"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>
        <Button type="submit" loading={isLoading || isFetching}>
          <Search className="w-4 h-4" />
          Rechercher
        </Button>
      </form>

      {error && (
        <div className="bg-red-900/20 border border-red-800/40 rounded-md px-4 py-3 text-sm text-red-400">
          {error instanceof Error ? error.message : 'Erreur de recherche'}
        </div>
      )}

      {result && (
        <Card>
          <div className="flex items-start justify-between mb-5">
            <div>
              <h2 className="text-base font-semibold text-zinc-100">{result.market_hash_name}</h2>
              <p className="text-xs text-zinc-500 mt-0.5">
                {result.skinport_quantity} listing{result.skinport_quantity !== 1 ? 's' : ''} sur Skinport
              </p>
            </div>
            <Button
              size="sm"
              variant="secondary"
              onClick={() =>
                addToWatchlist.mutate({ market_hash_name: result.market_hash_name })
              }
              loading={addToWatchlist.isPending}
            >
              <Plus className="w-3.5 h-3.5" />
              Watchlist
            </Button>
          </div>

          {addToWatchlist.isSuccess && (
            <div className="mb-4 bg-green-900/20 border border-green-800/40 rounded-md px-3 py-2 text-xs text-green-400">
              Ajouté à la watchlist
            </div>
          )}
          {addToWatchlist.isError && (
            <div className="mb-4 bg-red-900/20 border border-red-800/40 rounded-md px-3 py-2 text-xs text-red-400">
              {addToWatchlist.error instanceof Error
                ? addToWatchlist.error.message
                : 'Erreur'}
            </div>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
            <div>
              <h3 className="text-xs font-medium text-zinc-500 uppercase tracking-wider mb-3">
                CSFloat — Prix live
              </h3>
              <div className="flex justify-between items-center">
                <span className="text-xs text-zinc-500">Buy-now min</span>
                <span className="text-sm font-semibold text-zinc-100">
                  {result.csfloat_price_cents != null
                    ? formatEur(result.csfloat_price_cents)
                    : <span className="text-zinc-600">Non disponible</span>}
                </span>
              </div>
            </div>

            <div>
              <h3 className="text-xs font-medium text-zinc-500 uppercase tracking-wider mb-3">
                Skinport — Statistiques marché
              </h3>
              <div className="space-y-2">
                <div className="flex justify-between items-center">
                  <span className="text-xs text-zinc-500">Médiane</span>
                  <span className="text-sm font-medium text-zinc-200">
                    {formatEur(result.skinport_median_cents)}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-xs text-zinc-500">Minimum</span>
                  <span className="text-sm font-medium text-green-400">
                    {formatEur(result.skinport_min_cents)}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-xs text-zinc-500">Maximum</span>
                  <span className="text-sm font-medium text-red-400">
                    {formatEur(result.skinport_max_cents)}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </Card>
      )}
    </div>
  );
}
