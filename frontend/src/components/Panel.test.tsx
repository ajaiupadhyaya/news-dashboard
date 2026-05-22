import { render, screen } from '@testing-library/react';
import { renderWithProviders } from '../test/utils';
import { Panel } from './Panel';

test('renders a plain title when no href is given', () => {
  render(
    <Panel title="Finance" icon="💹">
      <p>body</p>
    </Panel>,
  );
  expect(screen.getByRole('heading', { name: 'Finance' })).toBeInTheDocument();
  expect(screen.queryByRole('link')).toBeNull();
});

test('renders the title as a link when href is given', () => {
  renderWithProviders(
    <Panel title="Finance" icon="💹" href="/finance">
      <p>body</p>
    </Panel>,
  );
  const link = screen.getByRole('link', { name: 'Open Finance' });
  expect(link).toHaveAttribute('href', '/finance');
});
