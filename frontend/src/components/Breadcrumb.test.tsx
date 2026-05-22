import { screen } from '@testing-library/react';
import { renderWithProviders } from '../test/utils';
import { Breadcrumb } from './Breadcrumb';

test('renders linked crumbs and a plain final crumb', () => {
  renderWithProviders(
    <Breadcrumb
      trail={[
        { label: 'Dashboard', to: '/' },
        { label: 'Finance', to: '/finance' },
        { label: 'AAPL' },
      ]}
    />,
  );
  // First crumb is prefixed with the back arrow.
  expect(screen.getByRole('link', { name: '← Dashboard' })).toBeInTheDocument();
  expect(screen.getByRole('link', { name: 'Finance' })).toBeInTheDocument();
  // The final crumb is the current page — text, not a link.
  expect(screen.queryByRole('link', { name: 'AAPL' })).toBeNull();
  expect(screen.getByText('AAPL')).toBeInTheDocument();
});
