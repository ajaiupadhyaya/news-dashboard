import { render, screen, fireEvent } from '@testing-library/react';
import { vi } from 'vitest';
import { RouterProvider, createMemoryRouter } from 'react-router-dom';
import { CommandPalette } from './CommandPalette';

function renderPalette(open = true) {
  const onClose = vi.fn();
  const router = createMemoryRouter(
    [{ path: '*', element: <CommandPalette open={open} onClose={onClose} /> }],
    { initialEntries: ['/'] },
  );
  render(<RouterProvider router={router} />);
  return { onClose, router };
}

test('shows destinations when open', () => {
  renderPalette(true);
  expect(screen.getByPlaceholderText(/Search/i)).toBeInTheDocument();
  expect(screen.getByText('Dashboard')).toBeInTheDocument();
});

test('renders nothing when closed', () => {
  renderPalette(false);
  expect(screen.queryByPlaceholderText(/Search/i)).not.toBeInTheDocument();
});

test('typing a ticker offers an instrument destination', () => {
  renderPalette(true);
  fireEvent.change(screen.getByPlaceholderText(/Search/i), {
    target: { value: 'nvda' },
  });
  expect(screen.getByText(/View instrument: NVDA/i)).toBeInTheDocument();
});

test('Escape closes the palette', () => {
  const { onClose } = renderPalette(true);
  fireEvent.keyDown(screen.getByPlaceholderText(/Search/i), { key: 'Escape' });
  expect(onClose).toHaveBeenCalled();
});
