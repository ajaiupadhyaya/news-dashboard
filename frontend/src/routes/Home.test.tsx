import { render, screen } from '@testing-library/react';
import { Home } from './Home';

test('renders the four-quadrant dashboard shell', () => {
  render(<Home />);
  expect(screen.getByText('NMD')).toBeInTheDocument();
  expect(screen.getByText('News')).toBeInTheDocument();
  expect(screen.getByText('Politics')).toBeInTheDocument();
  expect(screen.getByText('Economics')).toBeInTheDocument();
  expect(screen.getByText('Finance')).toBeInTheDocument();
});
