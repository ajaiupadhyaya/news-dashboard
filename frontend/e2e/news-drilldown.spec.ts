import { test, expect } from '@playwright/test';
import type { Page } from '@playwright/test';

const financeOverview = {
  watchlist: [],
  indices: [],
  sectors: [],
  breadth: { advancers: 0, decliners: 0, unchanged: 0, advance_decline_ratio: 0 },
  updated_at: '2026-05-22T20:00:00+00:00',
};

const economicsOverview = {
  indicators: [],
  calendar: [],
  updated_at: '2026-05-22T20:00:00+00:00',
};

const newsOverview = {
  stories: [
    {
      id: 'cluster-1',
      headline: 'A major story breaks across many outlets',
      summary: 'A short summary.',
      category: 'general',
      source_count: 6,
      article_count: 14,
      momentum: 3.1,
      status: 'surging',
      latest_published_at: '2026-05-22T19:00:00+00:00',
    },
  ],
  updated_at: '2026-05-22T20:00:00+00:00',
};

const storyDetail = {
  id: 'cluster-1',
  headline: 'A major story breaks across many outlets',
  summary: 'A short summary of the story.',
  category: 'general',
  source_count: 6,
  article_count: 14,
  momentum: 3.1,
  status: 'surging',
  articles: [
    {
      id: 'a1',
      title: 'First wire report',
      summary: 's',
      url: 'https://ex.com/a1',
      source: 'Reuters',
      published_at: '2026-05-22T16:00:00+00:00',
      category: 'general',
      image_url: null,
    },
  ],
  momentum_series: [
    { time: '2026-05-22T16:00:00+00:00', count: 1 },
    { time: '2026-05-22T17:00:00+00:00', count: 3 },
    { time: '2026-05-22T18:00:00+00:00', count: 7 },
  ],
  related: [],
  updated_at: '2026-05-22T20:00:00+00:00',
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
  await page.route('**/api/news/overview', (route) =>
    route.fulfill({ json: newsOverview }),
  );
  await page.route('**/api/news/story/**', (route) =>
    route.fulfill({ json: storyDetail }),
  );
}

test('the news overview drills down into a story page', async ({ page }) => {
  await stubApi(page);
  await page.goto('/');

  await expect(
    page.getByText('A major story breaks across many outlets').first(),
  ).toBeVisible();

  await page
    .getByRole('link', { name: /A major story breaks across many outlets/ })
    .click();

  await expect(page).toHaveURL(/\/news\/cluster-1$/);
  await expect(
    page.getByRole('heading', {
      name: 'A major story breaks across many outlets',
    }),
  ).toBeVisible();
  await expect(page.getByText('Development Timeline')).toBeVisible();
  await expect(page.getByText('First wire report')).toBeVisible();
});
