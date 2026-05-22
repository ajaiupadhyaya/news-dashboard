import { render, screen } from '@testing-library/react';
import { BentoGrid, BentoTile } from './BentoGrid';

test('renders tiles with their titles and content', () => {
  render(
    <BentoGrid>
      <BentoTile title="Indices" colSpan={2}>
        <p>tile body</p>
      </BentoTile>
      <BentoTile colSpan={4}>
        <p>untitled body</p>
      </BentoTile>
    </BentoGrid>,
  );
  expect(screen.getByRole('heading', { name: 'Indices' })).toBeInTheDocument();
  expect(screen.getByText('tile body')).toBeInTheDocument();
  expect(screen.getByText('untitled body')).toBeInTheDocument();
});

test('applies the column-span class for the requested span', () => {
  const { container } = render(
    <BentoGrid>
      <BentoTile colSpan={4}>
        <p>wide</p>
      </BentoTile>
    </BentoGrid>,
  );
  expect(container.querySelector('.lg\\:col-span-4')).not.toBeNull();
});
