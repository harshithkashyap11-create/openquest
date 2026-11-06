import { test, expect } from '@playwright/test';

test('teacher imports a source and selects support without assuming a diagnosis', async ({ page, request }) => {
  const classes = await request.get('/api/demo/classes').then(r => r.json());
  const c = classes.find(x => x.topic === 'Fractions');
  await page.addInitScript(s => sessionStorage.setItem('classpulse.demo-session', JSON.stringify(s)), { role: 'teacher', classId: c.id, subject: c.subject, topic: c.topic, className: c.class_name });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/teacher/inclusive');
  await expect(page.getByRole('heading', { name: 'Inclusive Learning' })).toBeVisible();
  await page.getByLabel('Import a lesson (PDF, DOCX, TXT or Markdown)').setInputFiles({ name: 'lesson.txt', mimeType: 'text/plain', buffer: Buffer.from('Plants need light and water to make their food.') });
  await expect(page.getByText('Lesson imported. Review the extracted source before adapting.')).toBeVisible();
  await page.getByText('Review extracted source').click();
  await expect(page.locator('details p').filter({ hasText: 'Plants need light and water' })).toBeVisible();
  await page.getByLabel(/Clear Instructions/).check();
  await expect(page.getByRole('button', { name: 'Create adaptation' })).toBeEnabled();
  await page.getByRole('button', { name: 'Create adaptation' }).click();
  await expect(page.getByText(/provider unavailable/i)).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});

test('student reader exposes adjustable presentation and practice', async ({ page, request }) => {
  const classes = await request.get('/api/demo/classes').then(r => r.json());
  const c = classes.find(x => x.topic === 'Fractions');
  const roster = await request.get(`/api/demo/classes/${c.id}/students`).then(r => r.json());
  const student = roster[0];
  await page.addInitScript(s => sessionStorage.setItem('classpulse.demo-session', JSON.stringify(s)), { role: 'student', classId: c.id, subject: c.subject, topic: c.topic, className: c.class_name, studentId: student.student_id });
  await page.route(`**/api/students/${student.student_id}/inclusive/lessons`, route => route.fulfill({ json: [{ id: 'a', content: { title: 'Plants', objectives: ['Identify plant needs'], text: 'Plants need light.', questions: [{ prompt: 'What do plants need?', hints: [] }] }, progress: null }] }));
  await page.route(`**/api/students/${student.student_id}/inclusive/lessons/a/practice`, route => route.fulfill({ json: { results: [{ correct: true }] } }));
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/student/inclusive');
  await expect(page.getByRole('heading', { name: 'Plants' })).toBeVisible();
  await page.getByLabel(/Text size/).fill('24');
  await expect(page.getByText('Plants need light.')).toHaveCSS('font-size', '24px');
  await page.getByLabel('What do plants need?').fill('light');
  await page.getByRole('button', { name: 'Check practice' }).click();
  await expect(page.getByText('That matches the answer.')).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});
