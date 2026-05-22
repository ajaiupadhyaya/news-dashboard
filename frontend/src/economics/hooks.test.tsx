import { vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryWrapper } from '../test/utils';
import { useEconomicsOverview, useIndicator } from './hooks';

vi.mock('../lib/api', () => ({
  api: {
    economicsOverview: vi.fn().mockResolvedValue({
      indicators: [],
      calendar: [],
      updated_at: '2026-05-21T00:00:00+00:00',
    }),
    indicator: vi.fn().mockResolvedValue({ series_id: 'UNRATE' }),
  },
}));

test('useEconomicsOverview fetches the overview', async () => {
  const { result } = renderHook(() => useEconomicsOverview(), {
    wrapper: QueryWrapper,
  });
  await waitFor(() => expect(result.current.isSuccess).toBe(true));
  expect(result.current.data?.updated_at).toBe('2026-05-21T00:00:00+00:00');
});

test('useIndicator fetches the requested series', async () => {
  const { result } = renderHook(() => useIndicator('UNRATE'), {
    wrapper: QueryWrapper,
  });
  await waitFor(() => expect(result.current.isSuccess).toBe(true));
  expect(result.current.data?.series_id).toBe('UNRATE');
});

test('useIndicator stays idle for an empty series id', () => {
  const { result } = renderHook(() => useIndicator(''), {
    wrapper: QueryWrapper,
  });
  expect(result.current.fetchStatus).toBe('idle');
});
