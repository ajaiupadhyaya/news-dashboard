import { render } from '@testing-library/react';
import { ChartFrame } from './ChartFrame';

test('renders a sized svg and gives children the inner dimensions', () => {
  let inner = { width: 0, height: 0 };
  const { container } = render(
    <ChartFrame
      width={200}
      height={100}
      margin={{ top: 10, right: 10, bottom: 10, left: 10 }}
    >
      {(d) => {
        inner = d;
        return <circle data-testid="mark" />;
      }}
    </ChartFrame>,
  );
  const svg = container.querySelector('svg')!;
  expect(svg.getAttribute('viewBox')).toBe('0 0 200 100');
  expect(inner).toEqual({ width: 180, height: 80 });
  expect(container.querySelector('[data-testid="mark"]')).not.toBeNull();
});
