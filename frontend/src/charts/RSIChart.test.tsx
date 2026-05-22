import { render } from '@testing-library/react';
import { RSIChart } from './RSIChart';

test('renders an RSI line and the 30/50/70 reference levels', () => {
  const values = Array.from({ length: 40 }, (_, i) =>
    i < 14 ? null : 40 + (i % 30),
  );
  const { container } = render(<RSIChart values={values} />);
  // 3 reference lines + 1 RSI path
  expect(container.querySelectorAll('line').length).toBe(3);
  expect(container.querySelectorAll('path').length).toBe(1);
});

test('renders nothing without enough RSI data', () => {
  const { container } = render(<RSIChart values={[null, null, null]} />);
  expect(container.querySelector('svg')).toBeNull();
});
