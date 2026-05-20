import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../lib/api';

/** The Finance overview — refetched every 60s to stay live. */
export function useOverview() {
  return useQuery({
    queryKey: ['overview'],
    queryFn: api.overview,
    refetchInterval: 60_000,
  });
}

/** A single instrument's drill-down data. Disabled for an empty symbol. */
export function useInstrument(symbol: string) {
  return useQuery({
    queryKey: ['instrument', symbol],
    queryFn: () => api.instrument(symbol),
    enabled: symbol.length > 0,
  });
}

/**
 * Add/remove watchlist mutations. The watchlist is part of the overview
 * response, so both invalidate the overview query on success.
 */
export function useWatchlistMutations() {
  const qc = useQueryClient();
  const invalidate = () => qc.invalidateQueries({ queryKey: ['overview'] });
  const add = useMutation({ mutationFn: api.addWatchlist, onSuccess: invalidate });
  const remove = useMutation({
    mutationFn: api.removeWatchlist,
    onSuccess: invalidate,
  });
  return { add, remove };
}
