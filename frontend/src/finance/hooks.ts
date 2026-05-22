import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query';
import { api } from '../lib/api';

/** The Finance overview — refetched every 60s to stay live. */
export function useOverview() {
  return useQuery({
    queryKey: ['overview'],
    queryFn: api.overview,
    refetchInterval: 60_000,
  });
}

/**
 * A single instrument's drill-down data for a timeframe range. Disabled for
 * an empty symbol. Keeps the previous data while a new range loads, so
 * switching timeframes does not flash the page.
 */
export function useInstrument(symbol: string, range = '1y') {
  return useQuery({
    queryKey: ['instrument', symbol, range],
    queryFn: () => api.instrument(symbol, range),
    enabled: symbol.length > 0,
    placeholderData: keepPreviousData,
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
