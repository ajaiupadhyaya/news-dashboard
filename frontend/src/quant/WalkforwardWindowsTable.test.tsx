import { render, screen } from '@testing-library/react';
import { WalkforwardWindowsTable } from './WalkforwardWindowsTable';
import type { WalkforwardWindow } from '../lib/quant-types';

const WINDOWS: WalkforwardWindow[] = [
  {
    train_start: '2020-01-01',
    train_end: '2022-12-31',
    test_start: '2023-01-01',
    test_end: '2023-12-31',
    chosen_params: { fast: 10, slow: 50 },
    oos_metrics: { sharpe: 1.42, total_return: 0.18 },
  },
  {
    train_start: '2021-01-01',
    train_end: '2023-12-31',
    test_start: '2024-01-01',
    test_end: '2024-12-31',
    chosen_params: { fast: 12, slow: 55 },
    oos_metrics: { sharpe: 0.87, total_return: 0.09 },
  },
];

test('renders the panel title', () => {
  render(<WalkforwardWindowsTable windows={WINDOWS} />);
  expect(screen.getByText('Walk-forward Windows')).toBeInTheDocument();
});

test('renders both window rows', () => {
  const { container } = render(<WalkforwardWindowsTable windows={WINDOWS} />);
  const rows = container.querySelectorAll('[data-testid^="window-row-"]');
  expect(rows).toHaveLength(2);
});

test('renders the train range for window 0', () => {
  render(<WalkforwardWindowsTable windows={WINDOWS} />);
  expect(screen.getByText('2020-01-01 – 2022-12-31')).toBeInTheDocument();
});

test('renders the test range for window 1', () => {
  render(<WalkforwardWindowsTable windows={WINDOWS} />);
  expect(screen.getByText('2024-01-01 – 2024-12-31')).toBeInTheDocument();
});

test('renders chosen params as k=v format', () => {
  render(<WalkforwardWindowsTable windows={WINDOWS} />);
  expect(screen.getByText('fast=10, slow=50')).toBeInTheDocument();
  expect(screen.getByText('fast=12, slow=55')).toBeInTheDocument();
});

test('renders OOS Sharpe values', () => {
  render(<WalkforwardWindowsTable windows={WINDOWS} />);
  expect(screen.getByText('1.42')).toBeInTheDocument();
  expect(screen.getByText('0.87')).toBeInTheDocument();
});

test('renders column headers', () => {
  render(<WalkforwardWindowsTable windows={WINDOWS} />);
  expect(screen.getByText('Train Range')).toBeInTheDocument();
  expect(screen.getByText('Test Range')).toBeInTheDocument();
  expect(screen.getByText('Chosen Params')).toBeInTheDocument();
  expect(screen.getByText('OOS Sharpe')).toBeInTheDocument();
});

test('shows empty state for empty windows array', () => {
  render(<WalkforwardWindowsTable windows={[]} />);
  expect(screen.getByText('No walk-forward windows')).toBeInTheDocument();
});
