import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query';
import { api } from '../lib/api';

export function useQuantOverview() {
  return useQuery({
    queryKey: ['quant', 'overview'],
    queryFn: api.quantOverview,
    refetchInterval: 60_000,
  });
}

export function useStrategy(slug: string) {
  return useQuery({
    queryKey: ['quant', 'strategy', slug],
    queryFn: () => api.quantStrategy(slug),
    enabled: slug.length > 0,
    placeholderData: keepPreviousData,
  });
}

export function useStrategyTrades(slug: string) {
  // Simple paginated cursor — for Q1d we use a single "load more" cursor.
  return useQuery({
    queryKey: ['quant', 'strategy-trades', slug],
    queryFn: () => api.quantStrategyTrades(slug, { limit: 100 }),
    enabled: slug.length > 0,
  });
}

export function useRecompute(slug: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.quantRecompute(slug),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['quant', 'strategy', slug] });
      qc.invalidateQueries({ queryKey: ['quant', 'overview'] });
    },
  });
}

export function useRunStatus(runId: number | null) {
  return useQuery({
    queryKey: ['quant', 'run', runId],
    queryFn: () => (runId ? api.quantRun(runId) : Promise.reject()),
    enabled: runId !== null,
    refetchInterval: (q) => {
      const status = q.state.data?.status;
      return status === 'pending' || status === 'running' ? 2000 : false;
    },
  });
}
