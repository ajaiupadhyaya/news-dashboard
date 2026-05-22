import { useQuery } from '@tanstack/react-query';
import { api } from '../lib/api';

/** The Economics overview — econ data moves slowly; refetch every 5 min. */
export function useEconomicsOverview() {
  return useQuery({
    queryKey: ['economics-overview'],
    queryFn: api.economicsOverview,
    refetchInterval: 300_000,
  });
}

/** One indicator's drill-down detail. Disabled for an empty series id. */
export function useIndicator(seriesId: string) {
  return useQuery({
    queryKey: ['indicator', seriesId],
    queryFn: () => api.indicator(seriesId),
    enabled: seriesId.length > 0,
  });
}
