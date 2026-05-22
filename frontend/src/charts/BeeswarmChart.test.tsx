import { render, fireEvent } from '@testing-library/react';
import { vi } from 'vitest';
import { BeeswarmChart } from './BeeswarmChart';
import type { StoryCluster } from '../lib/types';

function story(id: string, momentum: number, sources: number): StoryCluster {
  return {
    id,
    headline: `Story ${id}`,
    summary: 'summary',
    category: 'general',
    source_count: sources,
    article_count: sources,
    momentum,
    status: 'steady',
    latest_published_at: '2026-05-22T10:00:00Z',
  };
}

test('renders one circle per story', () => {
  const stories = [story('a', 2, 5), story('b', 1, 3), story('c', 0.5, 1)];
  const { container } = render(<BeeswarmChart stories={stories} />);
  expect(container.querySelectorAll('circle')).toHaveLength(3);
});

test('clicking a circle calls onSelect with the story id', () => {
  const onSelect = vi.fn();
  const { container } = render(
    <BeeswarmChart stories={[story('a', 2, 5)]} onSelect={onSelect} />,
  );
  fireEvent.click(container.querySelector('circle')!);
  expect(onSelect).toHaveBeenCalledWith('a');
});

test('renders nothing for an empty story list', () => {
  const { container } = render(<BeeswarmChart stories={[]} />);
  expect(container.querySelectorAll('circle')).toHaveLength(0);
});
