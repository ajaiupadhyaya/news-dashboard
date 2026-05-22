import { vi } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import { renderWithProviders } from '../test/utils';
import { StoryRoute } from './StoryRoute';

vi.mock('../lib/api', () => ({
  api: {
    story: vi.fn().mockResolvedValue({
      id: 'c1',
      headline: 'A clustered story headline',
      summary: 'A short summary of the story.',
      category: 'general',
      source_count: 3,
      article_count: 5,
      momentum: 2.4,
      status: 'surging',
      articles: [
        {
          id: 'a1',
          title: 'First report',
          summary: 's',
          url: 'https://ex.com/a1',
          source: 'Reuters',
          published_at: '2026-05-22T08:00:00Z',
          category: 'general',
          image_url: null,
        },
      ],
      momentum_series: [
        { time: '2026-05-22T08:00:00Z', count: 1 },
        { time: '2026-05-22T09:00:00Z', count: 2 },
        { time: '2026-05-22T10:00:00Z', count: 4 },
      ],
      related: [],
      updated_at: '2026-05-22T12:00:00+00:00',
    }),
  },
}));

test('renders the story headline, timeline, and sources', async () => {
  renderWithProviders(<StoryRoute />, {
    route: '/news/c1',
    path: '/news/:clusterId',
  });
  await waitFor(() =>
    expect(
      screen.getByRole('heading', { name: 'A clustered story headline' }),
    ).toBeInTheDocument(),
  );
  expect(screen.getByText('First report')).toBeInTheDocument();
  expect(screen.getByText('Development Timeline')).toBeInTheDocument();
  expect(screen.getByText('Sources')).toBeInTheDocument();
});
