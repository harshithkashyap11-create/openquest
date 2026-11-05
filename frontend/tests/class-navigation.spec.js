import { expect, test } from '@playwright/test';

test('teachers can switch among available classes without changing saved data', async ({ page, request }) => {
  const classes = await request.get('/api/demo/classes').then(response => response.json());
  const fractions = classes.find(item => item.topic === 'Fractions');
  const algebra = classes.find(item => item.topic === 'Basic algebra');
  expect(fractions).toBeTruthy();
  expect(algebra).toBeTruthy();
  await page.addInitScript(session => sessionStorage.setItem('classpulse.demo-session', JSON.stringify(session)), {
    role: 'teacher', classId: fractions.id, className: fractions.class_name,
    subject: fractions.subject, topic: fractions.topic,
  });
  await page.goto('/teacher/map');
  await expect(page.getByRole('heading', { name: 'Classroom Misconception Map' })).toBeVisible();
  await expect(page.locator('.topbar-class')).toContainText('Fractions');
  await expect(page.locator('body')).not.toContainText('Backend connected');
  await expect(page.locator('body')).not.toContainText('Synthetic Demo Class');
  await expect(page.locator('body')).not.toContainText('Demo access only');
  const picker = page.getByLabel('Choose class', { exact: true });
  await expect(picker.locator('option')).toHaveCount(classes.filter(item => item.subject === 'Mathematics').length);
  expect(await picker.locator('option').allTextContents()).not.toContain('Force and motion');
  await picker.selectOption(algebra.id);
  await expect(picker).toHaveValue(algebra.id);
  await expect(page.locator('.topbar-class')).toContainText('Basic algebra');
  await expect(page.locator('main')).toContainText('Mathematics');
  await expect(page).toHaveURL(/teacher\/map/);
  await picker.selectOption(fractions.id);
  await expect(picker).toHaveValue(fractions.id);
  await expect(page.locator('.topbar-class')).toContainText('Fractions');
  expect((await request.get('/api/demo/classes').then(response => response.json())).length).toBe(classes.length);
});
