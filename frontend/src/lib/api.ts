import type {
  EconomicsOverview,
  IndicatorDetail,
  InstrumentResponse,
  OverviewResponse,
} from './types';

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000';

/** Error thrown for any non-2xx response, carrying the HTTP status. */
export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

let authToken: string | null = null;

/** Set (or clear) the bearer token attached to every authed request. */
export function setAuthToken(token: string | null): void {
  authToken = token;
}

/** Fetch a JSON endpoint; throws ApiError on failure. */
export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  headers.set('Content-Type', 'application/json');
  if (authToken) headers.set('Authorization', `Bearer ${authToken}`);

  const res = await fetch(`${BASE_URL}${path}`, { ...init, headers });

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = (await res.json()) as { detail?: string };
      if (body?.detail) detail = body.detail;
    } catch {
      // response had no JSON body — keep the status text
    }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

/** Typed endpoint functions for the dashboard API. */
export const api = {
  authStatus: () => apiFetch<{ auth_enabled: boolean }>('/api/auth/status'),

  login: (password: string) =>
    apiFetch<{ token: string }>('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ password }),
    }),

  overview: () => apiFetch<OverviewResponse>('/api/finance/overview'),

  instrument: (symbol: string) =>
    apiFetch<InstrumentResponse>(
      `/api/finance/instrument/${encodeURIComponent(symbol)}`,
    ),

  addWatchlist: (symbol: string) =>
    apiFetch<{ symbols: string[] }>('/api/watchlist', {
      method: 'POST',
      body: JSON.stringify({ symbol }),
    }),

  removeWatchlist: (symbol: string) =>
    apiFetch<{ symbols: string[] }>(
      `/api/watchlist/${encodeURIComponent(symbol)}`,
      { method: 'DELETE' },
    ),

  economicsOverview: () =>
    apiFetch<EconomicsOverview>('/api/economics/overview'),

  indicator: (seriesId: string) =>
    apiFetch<IndicatorDetail>(
      `/api/economics/indicator/${encodeURIComponent(seriesId)}`,
    ),
};
