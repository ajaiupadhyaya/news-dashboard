import { vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryWrapper } from '../test/utils';
import { useOverview, useInstrument } from './hooks';

vi.mock('../lib/api', () => ({
  api: {
    overview: vi.fn().mockResolvedValue({
      watchlist: [], indices: [], sectors: [],
      breadth: { advancers: 0, decliners: 0, unchanged: 0, advance_decline_ratio: 0 },
      updated_at: '2026-05-20T20:00:00+00:00',
    }),
    instrument: vi.fn().mockResolvedValue({ symbol: 'AAPL' }),
  },
}));

test('useOverview fetches the finance overview', async () => {
  const { result } = renderHook(() => useOverview(), { wrapper: QueryWrapper });
  await waitFor(() => expect(result.current.isSuccess).toBe(true));
  expect(result.current.data?.updated_at).toBe('2026-05-20T20:00:00+00:00');
});

test('useInstrument fetches the requested symbol', async () => {
  const { result } = renderHook(() => useInstrument('AAPL'), {
    wrapper: QueryWrapper,
  });
  await waitFor(() => expect(result.current.isSuccess).toBe(true));
  expect(result.current.data?.symbol).toBe('AAPL');
});

test('useInstrument stays idle for an empty symbol', () => {
  const { result } = renderHook(() => useInstrument(''), {
    wrapper: QueryWrapper,
  });
  expect(result.current.fetchStatus).toBe('idle');
});
