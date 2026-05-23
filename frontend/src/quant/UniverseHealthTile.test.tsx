import { screen, render } from '@testing-library/react';
import { UniverseHealthTile } from './UniverseHealthTile';
import type { UniverseHealth } from '../lib/quant-types';

const health: UniverseHealth = {
  latest_bar_fetched_at: '2026-05-22T18:30:00Z',
  last_forward_step_per_strategy: {
    'sma-crossover': '2026-05-22',
    'buy-hold-spy': '2026-05-21',
    'news-momentum': null,
  },
};

test('renders last bar fetched timestamp', () => {
  render(<UniverseHealthTile health={health} />);
  expect(screen.getByText('2026-05-22T18:30:00Z')).toBeInTheDocument();
});

test('renders strategy slugs in the forward-step list', () => {
  render(<UniverseHealthTile health={health} />);
  expect(screen.getByText('sma-crossover')).toBeInTheDocument();
  expect(screen.getByText('buy-hold-spy')).toBeInTheDocument();
  expect(screen.getByText('news-momentum')).toBeInTheDocument();
});

test('renders forward step dates for known strategies', () => {
  render(<UniverseHealthTile health={health} />);
  expect(screen.getByText('2026-05-22')).toBeInTheDocument();
  expect(screen.getByText('2026-05-21')).toBeInTheDocument();
});

test('renders dash for null forward step', () => {
  render(<UniverseHealthTile health={health} />);
  // news-momentum has null — renders as "—"
  // Also latest_bar_fetched_at is non-null, so "—" comes from the null step
  expect(screen.getAllByText('—').length).toBeGreaterThan(0);
});

test('renders dash when latest_bar_fetched_at is null', () => {
  const noBar: UniverseHealth = {
    latest_bar_fetched_at: null,
    last_forward_step_per_strategy: {},
  };
  render(<UniverseHealthTile health={noBar} />);
  expect(screen.getByText('—')).toBeInTheDocument();
});
