import { vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import App from './App';

vi.mock('./lib/api', () => ({
  setAuthToken: vi.fn(),
  api: {
    authStatus: vi.fn().mockResolvedValue({ auth_enabled: false }),
  },
}));

test('renders the protected content once the auth status resolves', async () => {
  render(<App />);
  await waitFor(() =>
    expect(
      screen.getByText('News & Markets Dashboard'),
    ).toBeInTheDocument(),
  );
});
