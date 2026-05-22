import { renderHook, waitFor } from '@testing-library/react';
import { vi } from 'vitest';
import { QueryWrapper } from '../test/utils';
import { useNewsOverview, useStory } from './hooks';

vi.mock('../lib/api', () => ({
  api: {
    newsOverview: vi.fn().mockResolvedValue({ stories: [], updated_at: 'x' }),
    story: vi.fn().mockResolvedValue({ id: 'c1', headline: 'A story' }),
  },
}));

test('useNewsOverview fetches the overview', async () => {
  const { result } = renderHook(() => useNewsOverview(), {
    wrapper: QueryWrapper,
  });
  await waitFor(() => expect(result.current.isSuccess).toBe(true));
  expect(result.current.data?.stories).toEqual([]);
});

test('useStory fetches one story by id', async () => {
  const { result } = renderHook(() => useStory('c1'), {
    wrapper: QueryWrapper,
  });
  await waitFor(() => expect(result.current.isSuccess).toBe(true));
  expect(result.current.data?.id).toBe('c1');
});

test('useStory is disabled for an empty id', () => {
  const { result } = renderHook(() => useStory(''), {
    wrapper: QueryWrapper,
  });
  expect(result.current.fetchStatus).toBe('idle');
});
