import { QueryClientProvider } from '@tanstack/react-query';
import { MotionConfig } from 'motion/react';
import { RouterProvider } from 'react-router-dom';
import { AuthProvider } from './auth/AuthContext';
import { AuthGate } from './auth/AuthGate';
import { queryClient } from './lib/queryClient';
import { router } from './router';
import { spring } from './design/motion';

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <MotionConfig reducedMotion="user" transition={spring.smooth}>
        <AuthProvider>
          <AuthGate>
            <RouterProvider router={router} />
          </AuthGate>
        </AuthProvider>
      </MotionConfig>
    </QueryClientProvider>
  );
}
