import { render, screen } from '@testing-library/react';
import { MonthlyReturnsHeatmap } from './MonthlyReturnsHeatmap';

const ONE_YEAR_MATRIX: Record<string, Record<number, number>> = {
  '2025': {
    1: 0.035,
    2: -0.012,
    3: 0.021,
    4: 0.008,
    5: -0.025,
    6: 0.041,
    7: 0.019,
    8: -0.007,
    9: 0.031,
    10: 0.014,
    11: -0.003,
    12: 0.027,
  },
};

test('renders the panel title', () => {
  render(<MonthlyReturnsHeatmap matrix={ONE_YEAR_MATRIX} />);
  expect(screen.getByText('Monthly Returns')).toBeInTheDocument();
});

test('renders the year label for the fixture year', () => {
  render(<MonthlyReturnsHeatmap matrix={ONE_YEAR_MATRIX} />);
  expect(screen.getByText('2025')).toBeInTheDocument();
});

test('renders 12 month cells for a full year of data', () => {
  const { container } = render(<MonthlyReturnsHeatmap matrix={ONE_YEAR_MATRIX} />);
  const cells = container.querySelectorAll('[data-testid^="cell-2025-"]');
  expect(cells).toHaveLength(12);
});

test('renders all month abbreviation headers', () => {
  render(<MonthlyReturnsHeatmap matrix={ONE_YEAR_MATRIX} />);
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  for (const m of months) {
    expect(screen.getByText(m)).toBeInTheDocument();
  }
});

test('renders years in descending order (latest first)', () => {
  const multiYear: Record<string, Record<number, number>> = {
    '2023': { 1: 0.01 },
    '2025': { 1: 0.02 },
    '2024': { 1: 0.03 },
  };
  render(<MonthlyReturnsHeatmap matrix={multiYear} />);
  const table = screen.getByTestId('monthly-heatmap-table');
  const rows = table.querySelectorAll('tbody tr');
  expect(rows[0].textContent).toContain('2025');
  expect(rows[1].textContent).toContain('2024');
  expect(rows[2].textContent).toContain('2023');
});

test('shows empty state for empty matrix', () => {
  render(<MonthlyReturnsHeatmap matrix={{}} />);
  expect(screen.getByText('No monthly data')).toBeInTheDocument();
});

test('renders "—" for months with no data', () => {
  const sparse: Record<string, Record<number, number>> = {
    '2025': { 1: 0.05 }, // only January
  };
  const { container } = render(<MonthlyReturnsHeatmap matrix={sparse} />);
  // cells 2–12 should show em dash
  const cell2 = container.querySelector('[data-testid="cell-2025-2"]');
  expect(cell2?.textContent).toBe('—');
});
