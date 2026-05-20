import { vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { AuthGate } from './AuthGate';

const state = {
  ready: true,
  authed: true,
};
vi.mock('./AuthContext', () => ({
  useAuth: () => state,
}));
vi.mock('./LoginScreen', () => ({
  LoginScreen: () => <div>login-screen</div>,
}));

test('renders children when authed', () => {
  state.ready = true;
  state.authed = true;
  render(<AuthGate><div>protected</div></AuthGate>);
  expect(screen.getByText('protected')).toBeInTheDocument();
});

test('renders the login screen when not authed', () => {
  state.ready = true;
  state.authed = false;
  render(<AuthGate><div>protected</div></AuthGate>);
  expect(screen.getByText('login-screen')).toBeInTheDocument();
});

test('renders a loader before the auth status is known', () => {
  state.ready = false;
  state.authed = false;
  render(<AuthGate><div>protected</div></AuthGate>);
  expect(screen.getByRole('status')).toBeInTheDocument();
});
