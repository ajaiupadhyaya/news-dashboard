import { render, screen } from '@testing-library/react';
import { buildFundamentalCells, FundamentalsGrid } from './FundamentalsGrid';
import { StatsRow } from './StatsRow';
import type { Fundamentals } from '../lib/types';

const full: Fundamentals = {
  symbol: 'AAPL', name: 'Apple Inc.', sector: 'Technology',
  industry: 'Consumer Electronics', market_cap: 3.21e12, pe_ratio: 29.4,
  price_to_book: 48.1, dividend_yield: 0.5, week52_high: 240,
  week52_low: 160, beta: 1.2,
};

test('buildFundamentalCells formats the market cap compactly', () => {
  const cells = buildFundamentalCells(full);
  expect(cells.find((c) => c.label === 'Market Cap')?.value).toBe('3.21T');
});

test('buildFundamentalCells renders an em dash for missing values', () => {
  const cells = buildFundamentalCells({ ...full, pe_ratio: null, beta: null });
  expect(cells.find((c) => c.label === 'P/E')?.value).toBe('—');
  expect(cells.find((c) => c.label === 'Beta')?.value).toBe('—');
});

test('FundamentalsGrid renders every field label', () => {
  render(<FundamentalsGrid profile={full} />);
  expect(screen.getByText('Market Cap')).toBeInTheDocument();
  expect(screen.getByText('Beta')).toBeInTheDocument();
});

test('StatsRow renders momentum and volatility stats', () => {
  render(
    <StatsRow
      stats={{
        momentum_1m: 4.2, momentum_3m: 9.1, momentum_6m: -3.4,
        volatility_30d: 22.5, week52_high: 240, week52_low: 160,
      }}
    />,
  );
  expect(screen.getByText('1M')).toBeInTheDocument();
  expect(screen.getByText('+4.20%')).toBeInTheDocument();
  expect(screen.getByText('Vol 30D')).toBeInTheDocument();
  expect(screen.getByText('22.50%')).toBeInTheDocument();
});
