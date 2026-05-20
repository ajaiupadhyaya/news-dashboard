import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from 'react';
import type { ReactNode } from 'react';
import { api, setAuthToken } from '../lib/api';

const STORAGE_KEY = 'nmd.token';

interface AuthState {
  /** True once `/api/auth/status` has been checked. */
  ready: boolean;
  /** True when the backend has a token configured. */
  authRequired: boolean;
  token: string | null;
  /** True when access is allowed (auth not required, or a token is held). */
  authed: boolean;
  login: (password: string) => Promise<void>;
  logout: () => void;
}

const AuthCtx = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [ready, setReady] = useState(false);
  const [authRequired, setAuthRequired] = useState(false);
  const [token, setToken] = useState<string | null>(() =>
    localStorage.getItem(STORAGE_KEY),
  );

  useEffect(() => {
    setAuthToken(token);
  }, [token]);

  useEffect(() => {
    api
      .authStatus()
      .then((s) => setAuthRequired(s.auth_enabled))
      .catch(() => setAuthRequired(false))
      .finally(() => setReady(true));
  }, []);

  const login = useCallback(async (password: string) => {
    const { token: fresh } = await api.login(password);
    localStorage.setItem(STORAGE_KEY, fresh);
    setToken(fresh);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY);
    setToken(null);
  }, []);

  const authed = !authRequired || token !== null;

  return (
    <AuthCtx.Provider
      value={{ ready, authRequired, token, authed, login, logout }}
    >
      {children}
    </AuthCtx.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthCtx);
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider');
  return ctx;
}
