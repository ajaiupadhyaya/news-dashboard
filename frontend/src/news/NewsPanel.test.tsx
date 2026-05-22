import { vi } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import { renderWithProviders } from '../test/utils';
import { NewsPanel } from './NewsPanel';

vi.mock('../lib/api', () => ({
  api: {
    newsOverview: vi.fn().mockResolvedValue({
      stories: [
        {
          id: 'c1',
          headline: 'A clustered story headline',
          summary: 'summary',
          category: 'general',
          source_count: 4,
          article_count: 9,
          momentum: 2.3,
          status: 'surging',
          latest_published_at: '2026-05-22T10:00:00Z',
        },
      ],
      updated_at: '2026-05-22T12:00:00+00:00',
    }),
  },
}));

test('shows a loading skeleton before data arrives', () => {
  renderWithProviders(<NewsPanel />);
  expect(screen.getByRole('status')).toBeInTheDocument();
});

test('renders the story momentum field and the top-stories list', async () => {
  const { container } = renderWithProviders(<NewsPanel />);
  await waitFor(() =>
    expect(
      screen.getByText('A clustered story headline'),
    ).toBeInTheDocument(),
  );
  // the beeswarm hero renders one circle for the story
  expect(container.querySelectorAll('circle')).toHaveLength(1);
});
