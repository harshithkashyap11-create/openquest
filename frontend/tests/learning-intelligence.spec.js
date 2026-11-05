import { test, expect } from '@playwright/test';

test('lesson review, publication and mobile student access preserve provenance', async ({ page, request, browser }) => {
  const classes = await request.get('/api/demo/classes').then(r => r.json());
  const c = classes.find(c => c.topic === 'Fractions');
  const roster = await request.get(`/api/demo/classes/${c.id}/students`).then(r => r.json());
  const session = { role: 'teacher', classId: c.id, subject: c.subject, topic: c.topic, className: c.class_name };
  await page.addInitScript(s => sessionStorage.setItem('classpulse.demo-session', JSON.stringify(s)), session);
  await page.goto('/teacher/lessons');
  await expect(page.getByRole('heading', { name: 'Adaptive Lesson Studio', exact: true })).toBeVisible();
  await page.getByLabel('Teaching language').selectOption('te');
  await page.getByLabel('Misconception', { exact: true }).selectOption('M01');
  await page.getByRole('button', { name: 'Generate lesson draft', exact: true }).click();
  await expect(page.getByText('template', { exact: true }).first()).toBeVisible();
  await page.getByLabel('I reviewed the answer keys').check();
  await page.getByLabel('I reviewed the teaching language').check();
  await page.getByRole('button', { name: 'Approve revision', exact: true }).click();
  await page.getByRole('button', { name: 'Publish lesson', exact: true }).click();
  await expect(page.getByText('published', { exact: true }).first()).toBeVisible();
  const student = { ...session, role: 'student', studentId: roster[0].student_id, studentCode: roster[0].student_code };
  const context = await browser.newContext({ viewport: { width: 360, height: 780 } });
  await context.addInitScript(s => sessionStorage.setItem('classpulse.demo-session', JSON.stringify(s)), student);
  const learner = await context.newPage();
  await learner.goto('/student/learning');
  await expect(learner.getByRole('heading', { name: 'Learning Lab', exact: true })).toBeVisible();
  await expect(learner.getByText('సమాన భాగాలతో భిన్నాలను కూడండి')).toBeVisible();
  await learner.getByRole('button', { name: 'Download lesson', exact: true }).first().click();
  await expect(learner.getByText('Downloaded for this device', { exact: true }).first()).toBeVisible();
  expect(await learner.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await context.setOffline(true);
  await learner.reload();
  await expect(learner.getByText('సమాన భాగాలతో భిన్నాలను కూడండి')).toBeVisible();
  await context.close();
});

test('approved activity tutoring and offline practice synchronize to persisted evidence', async ({ page, request }, testInfo) => {
  const classes = await request.get('/api/demo/classes').then(r => r.json());
  const c = classes.find(x => x.topic === 'Fractions');
  const th = { 'X-Demo-Role': 'teacher', 'X-Class-ID': c.id };
  for (let i = 0; i < 15; i++) {
    const response = await request.post(`/api/classes/${c.id}/diagnose`, { headers: th });
    expect(response.ok()).toBe(true);
    if ((await response.json()).remaining_pending === 0) break;
  }
  const groups = await request.post(`/api/classes/${c.id}/groups/generate`, { headers: th }).then(r => r.json());
  const existing = await request.get(`/api/classes/${c.id}/groups`, { headers: th }).then(r => r.json());
  const group = [...groups.groups, ...existing].find(g => g.misconception_code === 'M01' && g.review_status !== 'rejected');
  expect(group).toBeTruthy();
  const reviewed = await request.patch(`/api/groups/${group.id}/review`, { headers: th, data: { status: 'approved', expected_revision: group.revision } });
  expect(reviewed.ok()).toBe(true);
  const generated = await request.post(`/api/groups/${group.id}/interventions/generate`, { headers: th }).then(r => r.json());
  const assignment = generated.assignments.find(a => a.status !== 'completed');
  expect(assignment).toBeTruthy();
  const sh = { 'X-Demo-Role': 'student', 'X-Student-ID': assignment.student_id };
  const before = await request.get(`/api/students/${assignment.student_id}/learning-state`, { headers: sh }).then(r => r.json());
  const session = { role: 'student', classId: c.id, className: c.class_name, subject: c.subject, topic: c.topic, studentId: assignment.student_id, studentCode: 'Synthetic learner' };
  await page.addInitScript(s => sessionStorage.setItem('classpulse.demo-session', JSON.stringify(s)), session);
  await page.setViewportSize({ width: 360, height: 780 });
  await page.goto('/student/learning');
  await page.getByRole('button', { name: 'Next guided hint', exact: true }).click();
  await expect(page.getByText('Hint 1', { exact: true })).toBeVisible();
  await page.getByLabel('Describe what you tried before the next hint').fill('I will find equal-sized parts.');
  await page.getByRole('button', { name: 'Next guided hint', exact: true }).click();
  await expect(page.getByText('Hint 2', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Download activity', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Downloaded for this device', exact: true })).toBeVisible();
  await page.context().setOffline(true);
  await page.reload();
  for (const [i, q] of assignment.intervention.practice_questions.entries()) {
    await page.getByLabel(q.question, { exact: true }).fill(generated.intervention.expected_answers[i]);
  }
  await page.getByRole('button', { name: 'Save practice responses', exact: true }).click();
  await expect(page.getByText('1 responses awaiting synchronization', { exact: true })).toBeVisible();
  await expect(page.locator('.backend-status')).toHaveText('Offline learning');
  await page.screenshot({ path: testInfo.outputPath('offline-practice-360.png'), fullPage: true });
  await page.context().setOffline(false);
  await expect.poll(async () => {
    const r = await request.get(`/api/intervention-assignments/${assignment.id}`, { headers: sh });
    return (await r.json()).practice_responses.length;
  }).toBe(3);
  await expect(page.getByText('0 responses awaiting synchronization', { exact: true })).toBeVisible();
  const after = await request.get(`/api/students/${assignment.student_id}/learning-state`, { headers: sh }).then(r => r.json());
  expect(after[0].independent_evidence_count).toBe(before[0].independent_evidence_count);
  expect(after[0].hint_count).toBe(2);
  await page.screenshot({ path: testInfo.outputPath('synchronized-practice-360.png'), fullPage: true });
});
