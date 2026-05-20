import { render, screen } from '@testing-library/react';
import { BreadthGauge } from './BreadthGauge';

test('renders advancer/decliner counts and the A/D ratio', () => {
  render(
    <BreadthGauge
      breadth={{
        advancers: 12,
        decliners: 4,
        unchanged: 1,
        advance_decline_ratio: 3,
      }}
    />,
  );
  expect(screen.getByText(/12 adv/)).toBeInTheDocument();
  expect(screen.getByText(/4 dec/)).toBeInTheDocument();
  expect(screen.getByText(/3\.00 A\/D/)).toBeInTheDocument();
});
