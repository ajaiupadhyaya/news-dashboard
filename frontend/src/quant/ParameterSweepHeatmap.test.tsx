import { render, screen } from '@testing-library/react';
import { ParameterSweepHeatmap } from './ParameterSweepHeatmap';
import type { ParameterSweepCell } from '../lib/quant-types';

const SWEEP: ParameterSweepCell[] = [
  { params: { a: 1, b: 10 }, sharpe: 0.5 },
  { params: { a: 1, b: 20 }, sharpe: 0.7 },
  { params: { a: 1, b: 30 }, sharpe: 0.4 },
  { params: { a: 2, b: 10 }, sharpe: 1.1 },
  { params: { a: 2, b: 20 }, sharpe: 1.3 },
  { params: { a: 2, b: 30 }, sharpe: 0.9 },
  { params: { a: 3, b: 10 }, sharpe: 0.8 },
  { params: { a: 3, b: 20 }, sharpe: 1.0 },
  { params: { a: 3, b: 30 }, sharpe: 0.6 },
];

const CHOSEN = { a: 2, b: 20 };

test('renders the panel title', () => {
  render(<ParameterSweepHeatmap sweep={SWEEP} chosen_params={CHOSEN} />);
  expect(screen.getByText('Parameter Sweep')).toBeInTheDocument();
});

test('renders the heatmap table for a valid sweep', () => {
  const { container } = render(
    <ParameterSweepHeatmap sweep={SWEEP} chosen_params={CHOSEN} />,
  );
  expect(container.querySelector('[data-testid="sweep-heatmap-table"]')).not.toBeNull();
});

test('renders 9 cells for a 3×3 grid', () => {
  const { container } = render(
    <ParameterSweepHeatmap sweep={SWEEP} chosen_params={CHOSEN} />,
  );
  const cells = container.querySelectorAll('[data-testid^="sweep-cell-"]');
  expect(cells).toHaveLength(9);
});

test('renders the star marker on the chosen params cell', () => {
  const { container } = render(
    <ParameterSweepHeatmap sweep={SWEEP} chosen_params={CHOSEN} />,
  );
  const marker = container.querySelector('[data-testid="chosen-marker"]');
  expect(marker).not.toBeNull();
  expect(marker?.textContent).toBe('★');
});

test('star appears specifically on the cell matching chosen params', () => {
  const { container } = render(
    <ParameterSweepHeatmap sweep={SWEEP} chosen_params={CHOSEN} />,
  );
  // Chosen is a=2, b=20 → cell-2-20
  const chosenCell = container.querySelector('[data-testid="sweep-cell-2-20"]');
  expect(chosenCell?.querySelector('[data-testid="chosen-marker"]')).not.toBeNull();

  // Cell a=1, b=10 must NOT have a star
  const otherCell = container.querySelector('[data-testid="sweep-cell-1-10"]');
  expect(otherCell?.querySelector('[data-testid="chosen-marker"]')).toBeNull();
});

test('shows empty-state message for empty sweep', () => {
  render(<ParameterSweepHeatmap sweep={[]} chosen_params={{}} />);
  expect(screen.getByText('No sweep grid for this strategy')).toBeInTheDocument();
});

test('handles single-param sweep gracefully', () => {
  const singleParam: ParameterSweepCell[] = [
    { params: { a: 1 }, sharpe: 0.5 },
    { params: { a: 2 }, sharpe: 0.8 },
  ];
  const { container } = render(
    <ParameterSweepHeatmap sweep={singleParam} chosen_params={{ a: 2 }} />,
  );
  // Should still render a table with 2 rows
  expect(container.querySelector('[data-testid="sweep-heatmap-table"]')).not.toBeNull();
});
