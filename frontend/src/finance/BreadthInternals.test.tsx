import { render, screen } from '@testing-library/react';
import { BreadthInternals } from './BreadthInternals';
import type { Breadth, WatchlistQuote } from '../lib/types';

const breadth: Breadth = {
  advancers: 6, decliners: 4, unchanged: 0, advance_decline_ratio: 1.5,
};
const vix: WatchlistQuote = {
  symbol: '^VIX', price: 14.2, change: -0.3, change_pct: -2.1, volume: 0,
  as_of: '2026-05-20', sparkline: [4, 3, 2, 1],
};

test('renders the breadth gauge and the VIX level', () => {
  render(<BreadthInternals breadth={breadth} vix={vix} />);
  expect(screen.getByText(/6 adv/)).toBeInTheDocument();
  expect(screen.getByText('VIX')).toBeInTheDocument();
  expect(screen.getByText('14.20')).toBeInTheDocument();
  expect(screen.getByText('-2.10%')).toBeInTheDocument();
});

test('omits the VIX block when no VIX quote is available', () => {
  render(<BreadthInternals breadth={breadth} vix={undefined} />);
  expect(screen.queryByText('VIX')).toBeNull();
  expect(screen.getByText(/6 adv/)).toBeInTheDocument();
});
