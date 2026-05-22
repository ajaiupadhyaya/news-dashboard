import { test, expect } from '@playwright/test';
import type { Page } from '@playwright/test';

const overview = {
  watchlist: [
    {
      symbol: 'AAPL', price: 212.5, change: 1.8, change_pct: 0.85,
      volume: 50_000_000, as_of: '2026-05-20',
      sparkline: [205, 207, 206, 209, 211, 210, 212.5],
    },
  ],
  indices: [
    {
      symbol: '^GSPC', price: 5400, change: 12, change_pct: 0.22,
      volume: 0, as_of: '2026-05-20',
    },
  ],
  sectors: [{ symbol: 'XLK', name: 'Technology', change_pct: 1.1 }],
  breadth: { advancers: 2, decliners: 0, unchanged: 0, advance_decline_ratio: 2 },
  updated_at: '2026-05-20T20:00:00+00:00',
};

function makeBars(n: number) {
  const bars = [];
  let price = 180;
  for (let i = 0; i < n; i++) {
    price += Math.sin(i / 7) * 2;
    const date = new Date(Date.UTC(2024, 0, 1 + i)).toISOString().slice(0, 10);
    bars.push({
      date,
      open: price,
      high: price + 3,
      low: price - 3,
      close: price + 1,
      volume: 1_000_000,
    });
  }
  return bars;
}

const bars = makeBars(120);

const instrument = {
  symbol: 'AAPL',
  profile: {
    symbol: 'AAPL', name: 'Apple Inc.', sector: 'Technology',
    industry: 'Consumer Electronics', market_cap: 3.21e12, pe_ratio: 29.4,
    price_to_book: 48.1, dividend_yield: 0.5, week52_high: 240,
    week52_low: 160, beta: 1.2,
  },
  bars,
  technicals: {
    sma_20: bars.map((b) => b.close),
    sma_50: bars.map((b) => b.close),
    sma_200: bars.map(() => null),
    rsi: bars.map((_, i) => (i < 14 ? null : 55)),
    macd_line: bars.map((_, i) => (i < 26 ? null : 0.4)),
    macd_signal: bars.map((_, i) => (i < 26 ? null : 0.2)),
    macd_histogram: bars.map((_, i) => (i < 26 ? null : 0.2)),
    bb_upper: bars.map((b) => b.close + 5),
    bb_middle: bars.map((b) => b.close),
    bb_lower: bars.map((b) => b.close - 5),
    volume: bars.map(() => 1000),
  },
  returns: {
    week_1: 1.2, month_1: -3.4, month_3: 8.0, month_6: 12.5,
    ytd: 6.1, year_1: 22.0, year_3: null,
  },
  stats: {
    momentum_1m: 4.2, momentum_3m: 9.1, momentum_6m: 15.3,
    volatility_30d: 22.5, week52_high: 240, week52_low: 160,
  },
  updated_at: '2026-05-20T20:00:00+00:00',
};

async function stubApi(page: Page) {
  await page.route('**/api/auth/status', (route) =>
    route.fulfill({ json: { auth_enabled: false } }),
  );
  await page.route('**/api/finance/overview', (route) =>
    route.fulfill({ json: overview }),
  );
  await page.route('**/api/finance/instrument/**', (route) =>
    route.fulfill({ json: instrument }),
  );
}

test('the overview drills down into an instrument page', async ({ page }) => {
  await stubApi(page);
  await page.goto('/');

  await expect(page.getByText('NMD')).toBeVisible();
  await expect(page.getByText('AAPL')).toBeVisible();

  await page.getByRole('link', { name: /AAPL/ }).click();

  await expect(page).toHaveURL(/\/finance\/AAPL$/);
  await expect(page.getByRole('heading', { name: 'AAPL' })).toBeVisible();
  await expect(page.getByText('Apple Inc.')).toBeVisible();
  await expect(page.getByText('Fundamentals')).toBeVisible();

  await expect(page.getByRole('group', { name: 'Timeframe' })).toBeVisible();
  await expect(page.getByText('RSI (14)')).toBeVisible();
  await expect(page.getByText('Returns')).toBeVisible();
  await page.getByRole('button', { name: '5Y' }).click();
  await expect(page.getByRole('button', { name: '5Y' })).toHaveAttribute(
    'aria-pressed',
    'true',
  );
});
