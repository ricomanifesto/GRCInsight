const path = require('node:path');
const { devices, expect, test } = require('@playwright/test');

const screenshotDirectory = process.env.STATIC_ARTIFACT_SCREENSHOTS;
const expectedDigest = process.env.STATIC_ARTIFACT_DIGEST;
const viewports = {
  desktop: { viewport: { width: 1440, height: 900 } },
  phone: { ...devices['Pixel 7'] },
};

function collectPageFailures(page) {
  const failures = [];
  page.on('console', (message) => {
    if (message.type() === 'error') failures.push(`console: ${message.text()}`);
  });
  page.on('pageerror', (error) => failures.push(`page: ${error.message}`));
  page.on('requestfailed', (request) => failures.push(`request: ${request.url()}`));
  page.on('response', (response) => {
    if (response.status() >= 400) failures.push(`${response.status()} ${response.url()}`);
  });
  return failures;
}

async function capture(page, testInfo, name) {
  const target = screenshotDirectory
    ? path.join(screenshotDirectory, `grcinsight-${name}.png`)
    : testInfo.outputPath(`${name}.png`);
  await page.screenshot({ path: target, fullPage: true });
}

async function horizontalOverflow(page) {
  return page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
}

async function newestArchive(page) {
  await page.goto('/archive/');
  const href = await page.locator('a[href$="Z/"]').first().getAttribute('href');
  expect(href).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}Z\/$/);
  return href;
}

test('the listener serves this GRCInsight artifact', async ({ request }) => {
  const response = await request.get('/');
  expect(response.ok()).toBeTruthy();
  const identity = response.headers()['x-static-artifact'] || '';
  expect(identity).toMatch(/^GRCInsight [0-9a-f]{64}$/);
  if (expectedDigest) expect(identity).toBe(`GRCInsight ${expectedDigest}`);
  expect(await response.text()).toContain('GRC Intelligence Report');
});

for (const [name, options] of Object.entries(viewports)) {
  test(`current and archived reports render from the artifact on ${name}`, async ({ browser }, testInfo) => {
    const context = await browser.newContext({ ...options, colorScheme: 'light', locale: 'en-US', timezoneId: 'UTC' });
    const page = await context.newPage();
    const failures = collectPageFailures(page);

    await page.goto('/');
    await expect(page.locator('.report-provenance')).toBeVisible();
    await expect(page.locator('nav.review-map')).toBeVisible();
    expect(await horizontalOverflow(page)).toBeLessThanOrEqual(1);
    await capture(page, testInfo, `current-${name}`);

    const archive = await newestArchive(page);
    await page.goto(`/archive/${archive}`);
    await expect(page.locator('h1')).toBeVisible();
    expect(await horizontalOverflow(page)).toBeLessThanOrEqual(1);
    await capture(page, testInfo, `archive-${archive.replace('/', '')}-${name}`);

    await page.goto('/publication-history/');
    await expect(page.locator('h1')).toBeVisible();
    expect(failures).toEqual([]);
    await context.close();
  });
}

test('the current report and retained notice are readable without JavaScript', async ({ browser, request }, testInfo) => {
  const context = await browser.newContext({ javaScriptEnabled: false });
  const page = await context.newPage();
  const response = await page.goto('/');
  expect(response?.ok()).toBeTruthy();

  await expect(page.locator('h1')).toContainText('GRC Intelligence Report');
  await expect(page.locator('.report-provenance')).toBeVisible();
  await expect(page.locator('h3[id^="finding-"]').first()).toBeVisible();
  const state = await (await request.get('/publication-state.json')).json();
  if (state.outcome === 'retained') await expect(page.locator('.publication-notice')).toBeVisible();
  await capture(page, testInfo, 'current-no-js');
  await context.close();
});

test('review map links land on their evidence headings and the theme toggles', async ({ page }) => {
  const failures = collectPageFailures(page);
  await page.goto('/');
  const link = page.locator('nav.review-map a[href^="#finding-"]').first();
  const target = (await link.getAttribute('href')).slice(1);
  await link.click();
  await expect.poll(() => new URL(page.url()).hash).toBe(`#${target}`);
  await expect(page.locator(`h3#${target}`)).toBeInViewport();

  const toggle = page.locator('#themeToggle');
  await expect(page.locator('body')).not.toHaveClass(/\bdark\b/);
  await toggle.click();
  await expect(page.locator('body')).toHaveClass(/\bdark\b/);
  await expect(toggle).toHaveAttribute('aria-label', 'Switch to light theme');
  await toggle.click();
  await expect(page.locator('body')).not.toHaveClass(/\bdark\b/);
  expect(failures).toEqual([]);
});
