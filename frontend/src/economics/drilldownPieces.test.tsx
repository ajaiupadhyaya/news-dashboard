import { render, screen } from '@testing-library/react';
import { RecessionSignals } from './RecessionSignals';
import { IndicatorStats } from './IndicatorStats';
import type { IndicatorDetail, RecessionSignal } from '../lib/types';

const signals: RecessionSignal[] = [
  {
    name: 'Yield curve (10y-2y)', value: -0.15, status: 'alert',
    detail: 'Inverted — historically a recession precursor.',
  },
  {
    name: 'Sahm rule', value: 0.1, status: 'normal',
    detail: 'Well below the Sahm-rule threshold.',
  },
];

const detail: IndicatorDetail = {
  series_id: 'UNRATE', name: 'Unemployment Rate', unit: '%',
  series: [{ date: '2026-04-01', value: 4.1 }],
  latest: 4.1, change: -0.1, yoy: 0.3, range_low: 3.4, range_high: 4.3,
  momentum: -2.4, recession_signals: signals,
  updated_at: '2026-05-21T00:00:00+00:00',
};

test('RecessionSignals lists each signal name and detail', () => {
  render(<RecessionSignals signals={signals} />);
  expect(screen.getByText('Yield curve (10y-2y)')).toBeInTheDocument();
  expect(
    screen.getByText('Inverted — historically a recession precursor.'),
  ).toBeInTheDocument();
  expect(screen.getByText('Sahm rule')).toBeInTheDocument();
});

test('IndicatorStats shows the headline stat tiles', () => {
  render(<IndicatorStats detail={detail} />);
  expect(screen.getByText('Latest')).toBeInTheDocument();
  expect(screen.getByText('4.1%')).toBeInTheDocument();
  expect(screen.getByText('YoY')).toBeInTheDocument();
  expect(screen.getByText('Momentum')).toBeInTheDocument();
});
