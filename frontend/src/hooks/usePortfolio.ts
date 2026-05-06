import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';

export function usePortfolioSummary() {
  return useQuery({
    queryKey: ['portfolio', 'summary'],
    queryFn: () => api.portfolio.summary(),
  });
}

export function usePortfolioHistory() {
  return useQuery({
    queryKey: ['portfolio', 'history'],
    queryFn: () => api.portfolio.history(),
  });
}
