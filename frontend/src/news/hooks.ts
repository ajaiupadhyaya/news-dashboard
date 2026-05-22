import { useQuery } from '@tanstack/react-query';
import { api } from '../lib/api';

/** The News overview — news moves fast; refetch every minute. */
export function useNewsOverview() {
  return useQuery({
    queryKey: ['news-overview'],
    queryFn: api.newsOverview,
    refetchInterval: 60_000,
  });
}

/** One story's drill-down detail. Disabled for an empty cluster id. */
export function useStory(clusterId: string) {
  return useQuery({
    queryKey: ['story', clusterId],
    queryFn: () => api.story(clusterId),
    enabled: clusterId.length > 0,
  });
}
