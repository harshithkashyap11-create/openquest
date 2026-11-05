import { expect, test } from '@playwright/test';

async function enter(page, request, topic = 'Fractions') {
  const classes = await request.get('/api/demo/classes').then(r => r.json());
  const c = classes.find(item => item.topic === topic);
  await page.addInitScript(s => sessionStorage.setItem('classpulse.demo-session', JSON.stringify(s)), {
    role: 'teacher', classId: c.id, className: c.class_name, subject: c.subject, topic: c.topic,
  });
  return c;
}

test('logo toggles the sidebar in place and the guide does not request diagnostics', async ({ page, request }) => {
  await enter(page, request);
  const diagnostics = [];
  page.on('request', r => { if (r.url().includes('/system-status')) diagnostics.push(r.url()); });
  await page.goto('/teacher/guide');
  await expect(page.getByRole('heading', { name: 'Student data', exact: true })).toBeVisible();
  const brand = page.locator('aside.sidebar').getByRole('button', { name: /ClassPulse AI/ });
  await brand.click();
  await expect(page.locator('.app-shell')).toHaveClass(/sidebar-collapsed/);
  await expect(page).toHaveURL(/teacher\/guide/);
  await brand.click();
  await expect(page.locator('.app-shell')).not.toHaveClass(/sidebar-collapsed/);
  await expect(page.locator('.topbar').getByLabel('Effects', { exact: true })).toHaveCount(0);
  await expect(page.getByRole('heading', { name: 'Local system status', exact: true })).toHaveCount(0);
  expect(diagnostics).toEqual([]);
});

test('insights charts share the full panel and learner evidence opens from collapsed details', async ({ page, request }, testInfo) => {
  await page.setViewportSize({ width: 1421, height: 900 });
  const c = await enter(page, request);
  for (let i = 0; i < 4; i++) {
    const r = await request.post(`/api/classes/${c.id}/diagnose`).then(r => r.json());
    if (!r.remaining_pending) break;
  }
  await page.goto('/teacher/insights');
  await expect(page.locator('.chart-panel')).toBeVisible();
  const details = page.locator('details.diagnosis-panel');
  await expect(details).not.toHaveAttribute('open');
  await expect(page.locator('.distribution-pie .recharts-pie')).toBeVisible();
  const panel = await page.locator('.chart-panel').boundingBox();
  const content = await page.locator('.insights-grid').boundingBox();
  expect(panel.width).toBeGreaterThan(content.width * 0.95);
  await details.locator('summary').click();
  await page.evaluate(() => window.scrollTo(0, 0));
  const evidence = details.getByRole('button', { name: /View evidence for/ }).first();
  await evidence.click();
  await expect(page.getByRole('dialog', { name: 'Diagnosis evidence', exact: true })).toBeVisible();
  await page.keyboard.press('Escape');
  await details.locator('summary').click();
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({ path: testInfo.outputPath('insights-desktop.png'), fullPage: true });
  await page.setViewportSize({ width: 360, height: 780 });
  await page.evaluate(() => window.scrollTo(0, 0));
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: testInfo.outputPath('insights-mobile.png'), fullPage: true });
});

test('empty assignments lead to group creation without hiding the page actions', async ({ page, request }) => {
  await enter(page, request, 'Basic algebra');
  await page.goto('/teacher/interventions#assignments');
  await expect(page.locator('main h1')).toBeInViewport();
  await expect(page.getByRole('link', { name: 'Review learning groups', exact: true })).toBeVisible();
  await page.getByRole('link', { name: 'Review learning groups', exact: true }).click();
  await expect(page).toHaveURL(/interventions#groups/);
  await expect(page.getByRole('button', { name: 'Generate groups', exact: true })).toBeInViewport();
  await expect(page.getByRole('link', { name: 'Review student answers', exact: true })).toBeVisible();
});

test('progress chart uses saved assessment stages and leaves missing follow-up scores unplotted', async ({ page, request }, testInfo) => {
  const c = await enter(page, request);
  const progress = await request.get(`/api/classes/${c.id}/progress`).then(r => r.json());
  await page.goto('/teacher/progress');
  await expect(page.locator('.progress-chart')).toBeVisible();
  const stages = page.locator('.progress-stage-data');
  await expect(stages).toContainText(`${progress.initial_assessment.accuracy_percentage}%`);
  if (!progress.followup_assessment.sample_size) {
    await expect(stages).toContainText('Not available');
    await expect(page.locator('.progress-chart .recharts-line-dot')).toHaveCount(1);
    expect(await page.locator('.progress-chart .recharts-line-curve').getAttribute('d') || '').not.toMatch(/[LC]/);
  } else {
    await expect(page.locator('.progress-chart .recharts-line-curve')).toBeVisible();
  }
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({ path: testInfo.outputPath('progress.png'), fullPage: true });
});
