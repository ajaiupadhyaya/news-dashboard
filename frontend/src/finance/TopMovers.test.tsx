import { screen } from '@testing-library/react';
import { renderWithProviders } from '../test/utils';
import { TopMovers } from './TopMovers';
import type { Mover } from '../lib/types';

const gainers: Mover[] = [
  { symbol: 'NVDA', price: 1200, change_pct: 3.4 },
];
const losers: Mover[] = [
  { symbol: 'INTC', price: 30, change_pct: -2.8 },
];

test('renders the gainers and losers sections', () => {
  renderWithProviders(<TopMovers gainers={gainers} losers={losers} />);
  expect(screen.getByText('Gainers')).toBeInTheDocument();
  expect(screen.getByText('Losers')).toBeInTheDocument();
  expect(screen.getByText('NVDA')).toBeInTheDocument();
  expect(screen.getByText('+3.40%')).toBeInTheDocument();
  expect(screen.getByText('-2.80%')).toBeInTheDocument();
  expect(screen.getByRole('link', { name: /NVDA/ })).toHaveAttribute(
    'href', '/finance/NVDA',
  );
  expect(screen.getByRole('link', { name: /INTC/ })).toHaveAttribute(
    'href', '/finance/INTC',
  );
});
