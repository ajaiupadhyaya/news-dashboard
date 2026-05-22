import { render, screen } from '@testing-library/react';
import { AssetClassStrip } from './AssetClassStrip';
import type { AssetClass } from '../lib/types';

const assetClasses: AssetClass[] = [
  { label: 'Equities', symbol: '^GSPC', price: 5400, change_pct: 0.4,
    sparkline: [1, 2, 3, 4] },
  { label: 'Crypto', symbol: 'BTC-USD', price: 68000, change_pct: -1.2,
    sparkline: [4, 3, 2, 1] },
];

test('renders a card for each asset class', () => {
  render(<AssetClassStrip assetClasses={assetClasses} />);
  expect(screen.getByText('Equities')).toBeInTheDocument();
  expect(screen.getByText('Crypto')).toBeInTheDocument();
  expect(screen.getByText('+0.40%')).toBeInTheDocument();
  expect(screen.getByText('-1.20%')).toBeInTheDocument();
  expect(screen.getByText('5,400.00')).toBeInTheDocument();
});
