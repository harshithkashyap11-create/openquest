import { test, expect } from '@playwright/test';

async function enter(page, role, classId) {
  await page.goto('/login');
  await page.getByRole('button', { name: role === 'student' ? /Student/ : /Teacher/ }).click();
  await page.getByLabel('Choose subject', { exact: true }).selectOption('Mathematics');
  await page.getByLabel('Choose topic', { exact: true }).selectOption('Fractions');
  await page.getByLabel('Choose class', { exact: true }).selectOption(classId);
  if (role === 'student') await page.getByLabel('Student code', { exact: true }).fill('DEMO-01');
  await page.getByRole('button', { name: role === 'student' ? /Continue as student/ : /Open teacher dashboard/ }).click();
  await expect(page).toHaveURL(role === 'student' ? /student\/dashboard/ : /teacher\/overview/);
}

test('fresh synthetic assessment → map review → approved support → reassessment → saved story', async ({ browser, request }, testInfo) => {
  const started = performance.now();
  const classes = await request.get('/api/demo/classes').then(r => r.json());
  expect(classes).toHaveLength(6);
  const c = classes.find(item => item.topic === 'Fractions');
  expect(c.class_name).toBe('Synthetic Fractions demonstration');
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 }, recordVideo: { dir: testInfo.outputPath('recording'), size: { width: 1280, height: 900 } } });
  const page = await context.newPage();
  page.setDefaultTimeout(15000);
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  await enter(page, 'student', c.id);
  await page.goto('/student/assessment');
  await page.getByLabel('Your answer', { exact: true }).fill('2/5');
  await page.getByLabel('Explanation (optional)', { exact: true }).fill('I added the numerators and denominators.');
  await page.getByRole('button', { name: 'Submit assessment', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Your answers were submitted. Your teacher can now review them.', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Sign out', exact: true }).click();
  await enter(page, 'teacher', c.id);
  await page.getByRole('button', { name: 'Diagnose new answers', exact: true }).click();
  await expect(page.getByRole('status').filter({ hasText: /Diagnosis finished/ })).toBeVisible();
  await page.getByRole('link', { name: 'Classroom Misconception Map', exact: true }).first().click();
  await page.getByRole('button', { name: /M01 ·/ }).click();
  await page.getByRole('button', { name: /Inspect response for DEMO-01/ }).click();
  const dialog = page.getByRole('dialog', { name: 'Response evidence', exact: true });
  await expect(dialog).toContainText('2/5');
  await dialog.getByLabel('Teacher decision', { exact: true }).selectOption('M01');
  await dialog.getByLabel('Reason for this review', { exact: true }).fill('Synthetic rehearsal: inspect the equal-sized-parts reasoning.');
  await dialog.getByRole('button', { name: 'Review correction', exact: true }).click();
  await dialog.getByRole('button', { name: 'Confirm and save', exact: true }).click();
  await expect(dialog.getByRole('status')).toContainText('Teacher decision saved');
  await page.keyboard.press('Escape');
  await page.getByRole('link', { name: 'Review groups and choose support', exact: true }).click();
  await page.getByRole('button', { name: 'Generate groups', exact: true }).click();
  await page.getByRole('button', { name: 'View members', exact: true }).click();
  await expect(page.getByRole('dialog', { name: 'Group members', exact: true })).toContainText('DEMO-01');
  await page.keyboard.press('Escape');
  await page.getByRole('button', { name: 'Approve', exact: true }).click();
  await page.getByRole('button', { name: 'Generate and assign intervention', exact: true }).click();
  await page.getByRole('dialog', { name: 'Generate for this group?', exact: true }).getByRole('button', { name: 'Generate and assign intervention', exact: true }).click();
  await expect(page.locator('.generated-intervention')).toBeVisible();
  await page.getByRole('button', { name: 'Sign out', exact: true }).click();
  await enter(page, 'student', c.id);
  await page.goto('/student/interventions');
  await page.getByRole('link', { name: 'Open activity', exact: true }).click();
  await page.getByRole('tab', { name: 'Try it', exact: true }).click();
  for (const [index, answer] of ['5/12', '1/2', '7/8'].entries()) {
    await page.getByLabel('Your answer', { exact: true }).fill(answer);
    if (index < 2) await page.getByRole('button', { name: 'Next question', exact: true }).click();
  }
  await page.getByRole('button', { name: 'Check practice answers', exact: true }).click();
  await page.getByRole('tab', { name: 'Finish & reassess', exact: true }).click();
  await page.getByRole('button', { name: 'Finish activity and start reassessment', exact: true }).click();
  await expect(page.locator('.reassessment-panel')).toBeVisible();
  for (const [index, answer] of ['11/12', '7/10', '13/24'].entries()) {
    await page.locator('input[id^="reassessment-"]:enabled').fill(answer);
    if (index < 2) await page.getByRole('button', { name: 'Next question', exact: true }).click();
  }
  await page.getByRole('button', { name: 'Submit check-in', exact: true }).click();
  await expect(page.locator('.result-summary')).toContainText('100%');
  await page.goto('/student/progress');
  await expect(page.locator('.journey-events')).toContainText('Assessment response saved');
  await expect(page.locator('.journey-events')).toContainText('Support assigned');
  await expect(page.locator('.journey-events')).toContainText('Reassessment result saved');
  await page.reload();
  await expect(page.locator('.journey-events')).toContainText('3 of 3 correct');
  await page.screenshot({ path: testInfo.outputPath('saved-progress.png'), fullPage: true });
  expect(errors).toEqual([]);
  await testInfo.attach('automated-duration-ms', { body: String(Math.round(performance.now() - started)), contentType: 'text/plain' });
  const video = page.video();
  await context.close();
  await video.saveAs(testInfo.outputPath('synthetic-fractions-mock-recording.webm'));
});
