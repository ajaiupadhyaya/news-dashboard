import { render } from '@testing-library/react';
import { Sparkline } from './Sparkline';

test('renders a line path, an area fill, and a gradient', () => {
  const { container } = render(
    <Sparkline values={[10, 12, 11, 14, 13, 16]} />,
  );
  expect(container.querySelectorAll('path')).toHaveLength(2);
  expect(container.querySelector('linearGradient')).not.toBeNull();
  const line = container.querySelectorAll('path')[1];
  expect(line.getAttribute('d')).toMatch(/^M/);
});

test('renders an empty svg without crashing for too-few points', () => {
  const { container } = render(<Sparkline values={[10]} />);
  expect(container.querySelector('svg')).not.toBeNull();
});
