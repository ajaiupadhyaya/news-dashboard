import { screen } from '@testing-library/react';
import { renderWithProviders } from '../test/utils';
import { IndicatorTile } from './IndicatorTile';
import type { IndicatorSummary } from '../lib/types';

const summary: IndicatorSummary = {
  series_id: 'UNRATE',
  name: 'Unemployment Rate',
  unit: '%',
  latest: 4.1,
  latest_date: '2026-04-01',
  change: -0.1,
  trend: 'in',
  sparkline: [4.3, 4.2, 4.1, 4.1],
};

test('renders the indicator name, value, and change', () => {
  renderWithProviders(<IndicatorTile summary={summary} />);
  expect(screen.getByText('Unemployment Rate')).toBeInTheDocument();
  expect(screen.getByText('4.1%')).toBeInTheDocument();
  expect(screen.getByText('-0.1pp')).toBeInTheDocument();
});

test('links to the indicator drill-down', () => {
  renderWithProviders(<IndicatorTile summary={summary} />);
  expect(screen.getByRole('link')).toHaveAttribute(
    'href',
    '/economics/UNRATE',
  );
});
