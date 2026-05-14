'use client';

import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { LogOut, RefreshCw } from 'lucide-react';
import { api } from '@/lib/api';
import { removeToken } from '@/lib/auth';
import { useSyncSkins } from '@/hooks/useSkins';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import type { UserSettingsUpdate } from '@/types';

export default function SettingsPage() {
  const router = useRouter();
  const queryClient = useQueryClient();

  const { data: settings, isLoading } = useQuery({
    queryKey: ['settings'],
    queryFn: () => api.settings.get(),
  });

  const updateMutation = useMutation({
    mutationFn: (data: UserSettingsUpdate) => api.settings.update(data),
    onSuccess: (updated) => {
      queryClient.setQueryData(['settings'], updated);
    },
  });

  const syncMutation = useSyncSkins();

  const [steamId, setSteamId] = useState('');
  const [discordId, setDiscordId] = useState('');
  const [thresholdUp, setThresholdUp] = useState('');
  const [thresholdDown, setThresholdDown] = useState('');
  const [showBackfillBanner, setShowBackfillBanner] = useState(false);
  const [backfillCount, setBackfillCount] = useState(0);
  const bannerTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (settings) {
      setSteamId(settings.steam_id ?? '');
      setDiscordId(settings.discord_id ?? '');
      setThresholdUp(String(Math.round(settings.threshold_up * 100)));
      setThresholdDown(String(Math.round(settings.threshold_down * 100)));
    }
  }, [settings]);

  useEffect(() => {
    if (!syncMutation.data) return;
    if (syncMutation.data.backfill_started) {
      setBackfillCount(syncMutation.data.backfill_count);
      setShowBackfillBanner(true);
      if (bannerTimerRef.current) clearTimeout(bannerTimerRef.current);
      bannerTimerRef.current = setTimeout(() => setShowBackfillBanner(false), 30_000);
    } else {
      setShowBackfillBanner(false);
      if (bannerTimerRef.current) {
        clearTimeout(bannerTimerRef.current);
        bannerTimerRef.current = null;
      }
    }
  }, [syncMutation.data]);

  useEffect(() => {
    return () => {
      if (bannerTimerRef.current) clearTimeout(bannerTimerRef.current);
    };
  }, []);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();

    const up = parseFloat(thresholdUp);
    const down = parseFloat(thresholdDown);

    const payload: UserSettingsUpdate = {
      steam_id: steamId || null,
      discord_id: discordId || null,
      ...(isFinite(up) ? { threshold_up: up / 100 } : {}),
      ...(isFinite(down) ? { threshold_down: down / 100 } : {}),
    };
    updateMutation.mutate(payload);
  }

  function handleLogout() {
    removeToken();
    void queryClient.clear();
    router.replace('/login');
  }

  function getSyncMessage(): string {
    if (!syncMutation.data) return '';
    const { new_skins, synced } = syncMutation.data;
    if (new_skins > 0) return `✅ ${synced} skins synchronisés, ${new_skins} nouveaux ajoutés`;
    return '✅ Inventaire à jour';
  }

  if (isLoading) {
    return (
      <div className="p-6 space-y-4">
        <div className="h-8 bg-zinc-800 animate-pulse rounded w-36" />
        <div className="h-56 bg-zinc-800 animate-pulse rounded-lg" />
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6 max-w-xl">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-zinc-100">Paramètres</h1>
          {settings && <p className="text-zinc-500 text-sm mt-0.5">{settings.email}</p>}
        </div>
        <Button variant="secondary" size="sm" onClick={handleLogout}>
          <LogOut className="w-3.5 h-3.5" />
          Déconnexion
        </Button>
      </div>

      {showBackfillBanner && (
        <div className="flex items-start gap-2 rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-300">
          <span className="shrink-0 mt-px">⏳</span>
          <span>
            Historique en cours de chargement pour{' '}
            <strong>{backfillCount}</strong> nouveaux skins — les graphiques seront disponibles
            dans quelques minutes
          </span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-5">
        <Card>
          <h2 className="text-xs font-medium text-zinc-500 uppercase tracking-wider mb-4">
            Comptes externes
          </h2>
          <div className="space-y-4">
            <Input
              label="Steam ID (SteamID64 ou URL de profil)"
              value={steamId}
              onChange={(e) => setSteamId(e.target.value)}
              placeholder="76561198..."
            />
            <Input
              label="Discord ID"
              value={discordId}
              onChange={(e) => setDiscordId(e.target.value)}
              placeholder="123456789012345678"
            />
          </div>

          <div className="mt-4 pt-4 border-t border-zinc-800 flex items-center gap-3">
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => syncMutation.mutate()}
              loading={syncMutation.isPending}
              disabled={!steamId}
              title={!steamId ? "Enregistre d'abord ton Steam ID" : undefined}
            >
              <RefreshCw className="w-3.5 h-3.5" />
              Sync inventaire Steam
            </Button>
            {syncMutation.isSuccess && (
              <span className="text-xs text-green-400">{getSyncMessage()}</span>
            )}
            {syncMutation.isError && (
              <span className="text-xs text-red-400">
                {syncMutation.error instanceof Error
                  ? syncMutation.error.message
                  : 'Erreur de sync'}
              </span>
            )}
          </div>
        </Card>

        <Card>
          <h2 className="text-xs font-medium text-zinc-500 uppercase tracking-wider mb-1">
            {"Seuils d'alerte"}
          </h2>
          <p className="text-xs text-zinc-600 mb-4">
            Hausse : déclenche EN HAUSSE quand le gain dépasse ce %. Retournement : déclenche
            ALERTE quand le recul depuis le pic dépasse ce %.
          </p>
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Seuil hausse (%)"
              type="number"
              step="1"
              min="1"
              max="500"
              value={thresholdUp}
              onChange={(e) => setThresholdUp(e.target.value)}
              placeholder="25"
            />
            <Input
              label="Seuil retournement (%)"
              type="number"
              step="1"
              min="1"
              max="100"
              value={thresholdDown}
              onChange={(e) => setThresholdDown(e.target.value)}
              placeholder="10"
            />
          </div>
        </Card>

        <div className="flex items-center gap-3">
          <Button type="submit" loading={updateMutation.isPending}>
            Enregistrer
          </Button>
          {updateMutation.isSuccess && (
            <span className="text-xs text-green-400">Paramètres sauvegardés</span>
          )}
          {updateMutation.isError && (
            <span className="text-xs text-red-400">
              {updateMutation.error instanceof Error
                ? updateMutation.error.message
                : 'Erreur'}
            </span>
          )}
        </div>
      </form>
    </div>
  );
}
