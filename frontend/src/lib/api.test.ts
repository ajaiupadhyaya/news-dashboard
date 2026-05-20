import { afterEach, vi } from 'vitest';
import { apiFetch, setAuthToken, api } from './api';

function mockFetch(status: number, body: unknown) {
  return vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    statusText: 'Error',
    json: async () => body,
  } as Response);
}

afterEach(() => {
  setAuthToken(null);
  vi.restoreAllMocks();
});

test('apiFetch parses JSON on a successful response', async () => {
  globalThis.fetch = mockFetch(200, { status: 'ok' });
  await expect(apiFetch('/health')).resolves.toEqual({ status: 'ok' });
});

test('apiFetch attaches a bearer token when one is set', async () => {
  const f = mockFetch(200, {});
  globalThis.fetch = f;
  setAuthToken('secret-token');
  await apiFetch('/api/finance/overview');
  const headers = new Headers((f.mock.calls[0][1] as RequestInit).headers);
  expect(headers.get('Authorization')).toBe('Bearer secret-token');
});

test('apiFetch throws an ApiError carrying status and detail', async () => {
  globalThis.fetch = mockFetch(404, { detail: 'No data for ZZZZ' });
  await expect(apiFetch('/api/finance/instrument/ZZZZ')).rejects.toMatchObject({
    status: 404,
    message: 'No data for ZZZZ',
  });
});

test('api.instrument URL-encodes symbols with special characters', async () => {
  const f = mockFetch(200, {});
  globalThis.fetch = f;
  await api.instrument('^GSPC');
  expect(f.mock.calls[0][0]).toContain('/api/finance/instrument/%5EGSPC');
});
