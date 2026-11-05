import { test, expect } from '@playwright/test';

async function setup(page, request) {
  const classes = await request.get('/api/demo/classes').then(r => r.json());
  const c = classes.find(x => x.topic === 'Fractions');
  for (let i = 0; i < 20; i++) {
    const response = await request.post(`/api/classes/${c.id}/diagnose`);
    expect(response.ok()).toBe(true);
    if (!(await response.json()).remaining_pending) break;
  }
  const session = { role: 'teacher', classId: c.id, className: c.class_name, subject: c.subject, topic: c.topic };
  await page.addInitScript(s => sessionStorage.setItem('classpulse.demo-session', JSON.stringify(s)), session);
  return c;
}

test('map evidence, confirmed correction and reviewed group route survive reload', async ({ page, request }) => {
  const c = await setup(page, request);
  await page.goto('/teacher/map');
  await expect(page.getByRole('heading', { name: 'Classroom Misconception Map', exact: true })).toBeVisible();
  const summary = await request.get(`/api/classes/${c.id}/misconception-map`).then(r => r.json());
  const m01 = summary.concepts.find(x => x.code === 'M01');
  expect(m01.response_count).toBeGreaterThan(0);
  const concept = page.getByRole('button', { name: /M01 ·/ }).first();
  await concept.focus();
  await page.keyboard.press('Enter');
  await expect(page.locator('.map-evidence')).toBeVisible();
  await page.getByRole('button', { name: /Inspect response/ }).first().click();
  const dialog = page.getByRole('dialog', { name: 'Response evidence', exact: true });
  await expect(dialog).toContainText('Student response');
  await expect(dialog).toContainText('Original AI suggestion');
  await dialog.getByLabel('Teacher decision', { exact: true }).selectOption('M01');
  await dialog.getByLabel('Reason for this review', { exact: true }).fill('Synthetic browser test: inspected response evidence.');
  await dialog.getByRole('button', { name: 'Review correction', exact: true }).click();
  await expect(dialog.getByRole('button', { name: 'Confirm and save', exact: true })).toBeVisible();
  // Lose the acknowledgement after a real server save. The next confirmation
  // must replay that request, not create a second correction.
  await page.route('**/diagnoses/*/corrections', async route => {
    if (route.request().method() !== 'POST') return route.continue();
    await route.fetch();
    await route.abort('failed');
  });
  await dialog.getByRole('button', { name: 'Confirm and save', exact: true }).click();
  await expect(dialog.getByRole('alert')).toContainText('Save confirmation is unavailable');
  await page.unroute('**/diagnoses/*/corrections');
  await dialog.getByRole('button', { name: 'Confirm and save', exact: true }).click();
  await expect(dialog.getByRole('status')).toContainText('Teacher decision saved');
  await expect(dialog).toContainText('Teacher reviewed');
  await page.reload();
  await concept.click();
  await page.getByRole('button', { name: /Inspect response/ }).first().click();
  await expect(dialog).toContainText('Teacher reviewed');
  await expect(dialog).toContainText('Original AI suggestion');
  await page.keyboard.press('Escape');
  await expect(page.getByRole('button', { name: /Inspect response/ }).first()).toBeFocused();
  await page.getByRole('link', { name: 'Review groups and choose support', exact: true }).click();
  await expect(page).toHaveURL(/interventions\?code=M01/);
});

test('map refresh failure retains data and translations fit a narrow screen', async ({ page, request }, testInfo) => {
  await setup(page, request);
  await page.setViewportSize({ width: 360, height: 780 });
  await page.goto('/teacher/map');
  await expect(page.locator('.concept-map')).toBeVisible();
  await page.route('**/misconception-map', route => route.fulfill({ status: 503, contentType: 'application/json', body: '{"detail":"unavailable"}' }));
  await page.getByRole('button', { name: 'Refresh', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('last loaded');
  await expect(page.locator('.concept-map')).toBeVisible();
  await page.unroute('**/misconception-map');
  await page.getByRole('button', { name: 'Try again', exact: true }).click();
  await expect(page.getByRole('alert')).toHaveCount(0);
  for (const locale of ['en', 'hi', 'te']) {
    await page.locator('.language-control select').selectOption(locale);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.screenshot({ path: testInfo.outputPath(`map-${locale}-360.png`), fullPage: true });
  }
  await page.locator('.language-control select').selectOption('en');
  await page.goto('/teacher/guide');
  await expect(page.getByRole('heading', { name: 'Student data', exact: true })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Local system status', exact: true })).toHaveCount(0);
  await expect(page.getByText('This page sends no support report.', { exact: false })).toBeVisible();
});
