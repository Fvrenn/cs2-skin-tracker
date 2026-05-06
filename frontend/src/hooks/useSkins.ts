import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';

export function useSkins() {
  return useQuery({
    queryKey: ['skins'],
    queryFn: () => api.skins.list(),
  });
}

export function useSkin(id: string) {
  return useQuery({
    queryKey: ['skins', id],
    queryFn: () => api.skins.get(id),
    enabled: !!id,
  });
}

export function useSyncSkins() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => api.skins.sync(),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['skins'] });
    },
  });
}

export function useSetPurchasePrice(skinId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (priceCents: number) => api.skins.setPurchasePrice(skinId, priceCents),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['skins'] });
      void queryClient.invalidateQueries({ queryKey: ['portfolio'] });
    },
  });
}
