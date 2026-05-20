import { render } from '@testing-library/react';
import { Axis } from './Axis';

test('renders one label per tick', () => {
  const { container } = render(
    <svg>
      <Axis
        orientation="left"
        ticks={[
          { value: 0, offset: 100, label: '0' },
          { value: 50, offset: 50, label: '50' },
          { value: 100, offset: 0, label: '100' },
        ]}
      />
    </svg>,
  );
  const texts = container.querySelectorAll('text');
  expect(texts).toHaveLength(3);
  expect(texts[1].textContent).toBe('50');
});
