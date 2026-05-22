import { render, screen } from '@testing-library/react';
import { StoryTimeline } from './StoryTimeline';
import { SourceList } from './SourceList';
import type { NewsArticle } from '../lib/types';

function article(id: string, source: string, hour: number): NewsArticle {
  return {
    id,
    title: `Headline ${id}`,
    summary: 'summary',
    url: `https://ex.com/${id}`,
    source,
    published_at: `2026-05-22T${String(hour).padStart(2, '0')}:00:00Z`,
    category: 'general',
    image_url: null,
  };
}

const articles = [
  article('a1', 'Reuters', 8),
  article('a2', 'BBC News', 9),
  article('a3', 'Reuters', 10),
];

test('StoryTimeline lists every article with its source', () => {
  render(<StoryTimeline articles={articles} />);
  expect(screen.getByText('Headline a1')).toBeInTheDocument();
  expect(screen.getByText('Headline a3')).toBeInTheDocument();
  expect(screen.getAllByText('Reuters')).toHaveLength(2);
});

test('StoryTimeline article links open in a new tab', () => {
  render(<StoryTimeline articles={[article('a1', 'Reuters', 8)]} />);
  const link = screen.getByRole('link', { name: /Headline a1/ });
  expect(link).toHaveAttribute('href', 'https://ex.com/a1');
  expect(link).toHaveAttribute('target', '_blank');
});

test('SourceList shows distinct sources with their article counts', () => {
  render(<SourceList articles={articles} />);
  expect(screen.getByText('Reuters')).toBeInTheDocument();
  expect(screen.getByText('BBC News')).toBeInTheDocument();
  expect(screen.getByText('2')).toBeInTheDocument(); // Reuters count
});
