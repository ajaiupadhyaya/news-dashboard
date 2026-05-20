import { vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { LoginScreen } from './LoginScreen';

const login = vi.fn();
vi.mock('./AuthContext', () => ({
  useAuth: () => ({ login }),
}));

test('submitting the form calls login with the password', async () => {
  login.mockResolvedValueOnce(undefined);
  render(<LoginScreen />);
  await userEvent.type(screen.getByLabelText('Password'), 'hunter2');
  await userEvent.click(screen.getByRole('button', { name: /enter/i }));
  expect(login).toHaveBeenCalledWith('hunter2');
});

test('shows an error message when login fails', async () => {
  login.mockRejectedValueOnce(new Error('bad'));
  render(<LoginScreen />);
  await userEvent.type(screen.getByLabelText('Password'), 'wrong');
  await userEvent.click(screen.getByRole('button', { name: /enter/i }));
  await waitFor(() =>
    expect(screen.getByText(/incorrect password/i)).toBeInTheDocument(),
  );
});
