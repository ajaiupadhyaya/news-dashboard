import { render, screen } from '@testing-library/react';
import { SectorHeatmap } from './SectorHeatmap';

test('renders a cell for each sector', () => {
  render(
    <SectorHeatmap
      sectors={[
        { symbol: 'XLK', name: 'Technology', change_pct: 1.2 },
        { symbol: 'XLF', name: 'Financials', change_pct: -0.5 },
        { symbol: 'XLE', name: 'Energy', change_pct: 0 },
      ]}
    />,
  );
  expect(screen.getByText('XLK')).toBeInTheDocument();
  expect(screen.getByText('XLF')).toBeInTheDocument();
  expect(screen.getByText('XLE')).toBeInTheDocument();
});
