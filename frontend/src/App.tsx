import { QueryClientProvider } from '@tanstack/react-query';
import { MotionConfig } from 'motion/react';
import { AuthProvider } from './auth/AuthContext';
import { AuthGate } from './auth/AuthGate';
import { queryClient } from './lib/queryClient';
import { spring } from './design/motion';

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <MotionConfig reducedMotion="user" transition={spring.smooth}>
        <AuthProvider>
          <AuthGate>
            <div>News &amp; Markets Dashboard</div>
          </AuthGate>
        </AuthProvider>
      </MotionConfig>
    </QueryClientProvider>
  );
}
