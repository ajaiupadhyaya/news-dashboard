import type { ReactElement, ReactNode } from 'react';
import { render } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { RouterProvider, createMemoryRouter } from 'react-router-dom';

/** A fresh QueryClient with retries off — isolates each test. */
export function makeQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
}

interface RenderOptions {
  /** Initial URL. */
  route?: string;
  /** Route pattern, e.g. "/finance/:symbol" when the UI reads params. */
  path?: string;
}

/**
 * Render `ui` inside a data router + QueryClientProvider. A data router
 * (not <MemoryRouter>) is required for `<Link viewTransition>` and
 * `useViewTransitionState` to work in tests.
 */
export function renderWithProviders(
  ui: ReactElement,
  { route = '/', path = '*' }: RenderOptions = {},
) {
  const qc = makeQueryClient();
  const router = createMemoryRouter(
    [
      {
        path,
        element: <QueryClientProvider client={qc}>{ui}</QueryClientProvider>,
      },
    ],
    { initialEntries: [route] },
  );
  return { qc, router, ...render(<RouterProvider router={router} />) };
}

/** Convenience wrapper component for `renderHook`. */
export function QueryWrapper({ children }: { children: ReactNode }) {
  const qc = makeQueryClient();
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}
