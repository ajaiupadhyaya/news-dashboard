import { screen } from '@testing-library/react';
import { renderWithProviders } from '../test/utils';
import { StoryRow } from './StoryRow';
import type { StoryCluster } from '../lib/types';

const story: StoryCluster = {
  id: 'c1',
  headline: 'A major development unfolds',
  summary: 'summary',
  category: 'general',
  source_count: 3,
  article_count: 8,
  momentum: 2.1,
  status: 'surging',
  latest_published_at: '2026-05-22T10:00:00Z',
};

test('renders the headline, status, and source count', () => {
  renderWithProviders(<StoryRow story={story} />);
  expect(screen.getByText(/A major development unfolds/)).toBeInTheDocument();
  expect(screen.getByText('Surging')).toBeInTheDocument();
  expect(screen.getByText('3 sources')).toBeInTheDocument();
});

test('links to the story drill-down', () => {
  renderWithProviders(<StoryRow story={story} />);
  expect(screen.getByRole('link')).toHaveAttribute('href', '/news/c1');
});
