import { useState } from 'react';
import type { FormEvent } from 'react';
import { motion } from 'motion/react';
import { useAuth } from './AuthContext';
import { spring } from '../design/motion';

export function LoginScreen() {
  const { login } = useAuth();
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(password);
    } catch {
      setError('Incorrect password');
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-full items-center justify-center bg-bg p-6">
      <motion.form
        onSubmit={onSubmit}
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={spring.gentle}
        className="w-full max-w-sm rounded-lg border border-border bg-surface p-8"
      >
        <h1 className="font-mono text-xs tracking-widest text-ink-mute uppercase">
          News &amp; Markets
        </h1>
        <p className="mt-1 text-lg font-medium text-ink">Sign in</p>

        <input
          type="password"
          aria-label="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoFocus
          className="mt-6 w-full rounded-md border border-border bg-raised px-3 py-2
                     text-ink outline-none transition-colors focus:border-accent"
        />

        {error && (
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="mt-2 text-sm text-down"
          >
            {error}
          </motion.p>
        )}

        <motion.button
          type="submit"
          disabled={busy}
          whileTap={{ scale: 0.97 }}
          className="mt-6 w-full rounded-md bg-accent py-2 font-medium text-bg
                     transition-opacity disabled:opacity-50"
        >
          {busy ? 'Signing in…' : 'Enter'}
        </motion.button>
      </motion.form>
    </div>
  );
}
