import { beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AuthProvider, useAuth } from './AuthContext';

vi.mock('../lib/api', () => ({
  setAuthToken: vi.fn(),
  api: {
    authStatus: vi.fn().mockResolvedValue({ auth_enabled: true }),
    login: vi.fn().mockResolvedValue({ token: 'tok-123' }),
  },
}));

function Probe() {
  const { ready, authed, login } = useAuth();
  return (
    <div>
      <span>ready:{String(ready)}</span>
      <span>authed:{String(authed)}</span>
      <button onClick={() => void login('pw')}>do-login</button>
    </div>
  );
}

beforeEach(() => localStorage.clear());

test('reports auth required and unauthed before login', async () => {
  render(<AuthProvider><Probe /></AuthProvider>);
  await waitFor(() => expect(screen.getByText('ready:true')).toBeInTheDocument());
  expect(screen.getByText('authed:false')).toBeInTheDocument();
});

test('login stores a token and flips to authed', async () => {
  render(<AuthProvider><Probe /></AuthProvider>);
  await waitFor(() => expect(screen.getByText('ready:true')).toBeInTheDocument());
  await userEvent.click(screen.getByText('do-login'));
  await waitFor(() => expect(screen.getByText('authed:true')).toBeInTheDocument());
  expect(localStorage.getItem('nmd.token')).toBe('tok-123');
});
