import { test, expect } from '@playwright/test';
import type { Page } from '@playwright/test';

const financeOverview = {
  watchlist: [],
  indices: [],
  sectors: [],
  breadth: { advancers: 0, decliners: 0, unchanged: 0, advance_decline_ratio: 0 },
  updated_at: '2026-05-21T20:00:00+00:00',
};

const economicsOverview = {
  indicators: [
    {
      series_id: 'UNRATE', name: 'Unemployment Rate', unit: '%',
      latest: 4.1, latest_date: '2026-04-01', change: -0.1,
      trend: 'in', sparkline: [4.3, 4.2, 4.1, 4.0, 4.1],
    },
  ],
  calendar: [{ date: '2026-05-13', release_name: 'Consumer Price Index' }],
  updated_at: '2026-05-21T20:00:00+00:00',
};

function makeSeries(n: number) {
  return Array.from({ length: n }, (_, i) => ({
    date: new Date(Date.UTC(2026, 0, 1 + i)).toISOString().slice(0, 10),
    value: 4 + Math.sin(i / 6) * 0.6,
  }));
}

const indicatorDetail = {
  series_id: 'UNRATE', name: 'Unemployment Rate', unit: '%',
  series: makeSeries(120),
  latest: 4.1, change: -0.1, yoy: 0.3, range_low: 3.4, range_high: 4.3,
  momentum: -2.4,
  recession_signals: [
    {
      name: 'Yield curve (10y-2y)', value: -0.15, status: 'alert',
      detail: 'Inverted — historically a recession precursor.',
    },
  ],
  updated_at: '2026-05-21T20:00:00+00:00',
};

async function stubApi(page: Page) {
  await page.route('**/api/auth/status', (route) =>
    route.fulfill({ json: { auth_enabled: false } }),
  );
  await page.route('**/api/finance/overview', (route) =>
    route.fulfill({ json: financeOverview }),
  );
  await page.route('**/api/economics/overview', (route) =>
    route.fulfill({ json: economicsOverview }),
  );
  await page.route('**/api/economics/indicator/**', (route) =>
    route.fulfill({ json: indicatorDetail }),
  );
}

test('the economics overview drills down into an indicator page', async ({
  page,
}) => {
  await stubApi(page);
  await page.goto('/');

  await expect(page.getByText('NMD')).toBeVisible();
  await expect(page.getByText('Unemployment Rate')).toBeVisible();

  await page.getByRole('link', { name: /Unemployment Rate/ }).click();

  await expect(page).toHaveURL(/\/economics\/UNRATE$/);
  await expect(
    page.getByRole('heading', { name: 'Unemployment Rate' }),
  ).toBeVisible();
  await expect(page.getByText('Recession Signals')).toBeVisible();
});
