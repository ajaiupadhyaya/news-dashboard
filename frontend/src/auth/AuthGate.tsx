import type { ReactNode } from 'react';
import { useAuth } from './AuthContext';
import { LoginScreen } from './LoginScreen';

function FullScreenLoader() {
  return (
    <div
      role="status"
      aria-label="Loading"
      className="flex min-h-full items-center justify-center bg-bg"
    >
      <div className="h-6 w-6 animate-spin rounded-full border-2 border-border
                      border-t-accent" />
    </div>
  );
}

export function AuthGate({ children }: { children: ReactNode }) {
  const { ready, authed } = useAuth();
  if (!ready) return <FullScreenLoader />;
  if (!authed) return <LoginScreen />;
  return <>{children}</>;
}
