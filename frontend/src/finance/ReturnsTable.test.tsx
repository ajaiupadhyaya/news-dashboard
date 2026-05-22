import { render, screen } from '@testing-library/react';
import { ReturnsTable } from './ReturnsTable';
import type { Returns } from '../lib/types';

const returns: Returns = {
  week_1: 1.2, month_1: -3.4, month_3: 8.0, month_6: 12.5,
  ytd: 6.1, year_1: 22.0, year_3: null,
};

test('renders a labeled cell per period', () => {
  render(<ReturnsTable returns={returns} />);
  expect(screen.getByText('1W')).toBeInTheDocument();
  expect(screen.getByText('YTD')).toBeInTheDocument();
  expect(screen.getByText('3Y')).toBeInTheDocument();
  expect(screen.getByText('+1.20%')).toBeInTheDocument();
  expect(screen.getByText('-3.40%')).toBeInTheDocument();
});

test('shows a dash for a missing period', () => {
  render(<ReturnsTable returns={returns} />);
  // 3Y is null
  expect(screen.getByText('—')).toBeInTheDocument();
});
