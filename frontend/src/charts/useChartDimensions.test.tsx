import { render, screen } from '@testing-library/react';
import { useChartDimensions } from './useChartDimensions';

function Probe() {
  const [ref, dims] = useChartDimensions<HTMLDivElement>({
    width: 300,
    height: 150,
  });
  return <div ref={ref}>{`${dims.width}x${dims.height}`}</div>;
}

test('returns the fallback dimensions when the element is unmeasured', () => {
  render(<Probe />);
  expect(screen.getByText('300x150')).toBeInTheDocument();
});
