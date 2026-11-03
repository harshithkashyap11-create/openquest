import { expect, test } from '@playwright/test';

async function demo(request, role = 'teacher') {
  const classes = await request.get('/api/demo/classes').then((r) => r.json());
  const c = classes.find((c) => c.topic === 'Fractions');
  const roster = await request
    .get(`/api/demo/classes/${c.id}/students`)
    .then((r) => r.json());
  return {
    role,
    classId: c.id,
    className: c.class_name,
    subject: c.subject,
    topic: c.topic,
    ...(role === 'student'
      ? { studentId: roster[0].student_id, studentCode: roster[0].student_code }
      : {}),
  };
}
async function enter(page, session) {
  await page.addInitScript(
    (s) => sessionStorage.setItem('classpulse.demo-session', JSON.stringify(s)),
    session,
  );
}

test('Lite preference persists and reduced motion overrides full effects without losing class context', async ({
  page,
  request,
}) => {
  const s = await demo(request);
  await enter(page, s);
  await page.goto('/teacher/overview');
  const effects = page.getByLabel('Effects', { exact: true });
  await effects.selectOption('lite');
  await expect(page.locator('html')).toHaveAttribute('data-effects', 'lite');
  await page.reload();
  await expect(effects).toHaveValue('lite');
  await effects.selectOption('full');
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await expect(page.locator('html')).toHaveAttribute('data-effects', 'lite');
  await page.getByLabel('Language', { exact: true }).focus();
  await page.getByLabel('Language', { exact: true }).selectOption('te');
  await expect(page.locator('.topbar-class')).toContainText(s.className);
  expect(await page.evaluate(() => document.activeElement?.tagName)).toBe(
    'SELECT',
  );
});

test('mobile navigation traps focus, closes with Escape and restores its trigger', async ({
  page,
  request,
}) => {
  await page.setViewportSize({ width: 360, height: 780 });
  await enter(page, await demo(request));
  await page.goto('/teacher/overview');
  const trigger = page.getByRole('button', {
    name: 'Open navigation',
    exact: true,
  });
  await trigger.click();
  const dialog = page.getByRole('dialog', { name: 'Navigation', exact: true });
  await expect(dialog).toBeVisible();
  await dialog.locator('button,a[href],select').last().focus();
  await page.keyboard.press('Tab');
  expect(await dialog.evaluate((n) => n.contains(document.activeElement))).toBe(
    true,
  );
  await page.keyboard.press('Escape');
  await expect(dialog).not.toBeVisible();
  await expect(trigger).toBeFocused();
  expect(await page.evaluate(() => document.body.style.overflow)).not.toBe(
    'hidden',
  );
  await trigger.click();
  await dialog
    .getByRole('link', { name: 'Class insights', exact: true })
    .click();
  await expect(page).toHaveURL(/insights/);
  await expect(dialog).not.toBeVisible();
  await expect(page.locator('main h1')).toBeFocused();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
});

test('question navigation and language changes preserve answers; failed submission can retry', async ({
  page,
  request,
}) => {
  await enter(page, await demo(request, 'student'));
  await page.goto('/student/assessment');
  const answer = page.getByLabel('Your answer', { exact: true });
  await answer.fill('5/6');
  await page
    .getByLabel('Explanation (optional)', { exact: true })
    .fill('Use equal parts.');
  await page
    .getByRole('button', { name: 'Next question', exact: true })
    .click();
  await answer.fill('3/4');
  await page
    .getByRole('button', { name: 'Previous question', exact: true })
    .click();
  await expect(answer).toHaveValue('5/6');
  await page.getByLabel('Language', { exact: true }).selectOption('hi');
  await expect(page.locator('input[id^="answer-"]')).toHaveValue('5/6');
  await page.locator('.language-control select').selectOption('en');
  const next = page.getByRole('button', { name: 'Next question', exact: true });
  while (await next.count()) {
    await next.click();
    await answer.fill('1');
  }
  await page.route('**/assessment-submissions', (r) =>
    r.fulfill({
      status: 503,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'Temporary outage. Retry your answers.' }),
    }),
  );
  await page
    .getByRole('button', { name: 'Submit assessment', exact: true })
    .click();
  await expect(page.getByRole('alert')).toContainText('Temporary outage');
  await expect(answer).toHaveValue('1');
  await page.unroute('**/assessment-submissions');
  await page
    .getByRole('button', { name: 'Submit assessment', exact: true })
    .click();
  await expect(
    page.getByRole('heading', {
      name: 'Your answers were submitted. Your teacher can now review them.',
      exact: true,
    }),
  ).toBeVisible();
});

test('route history preserves focus and only one active main heading during rapid navigation', async ({
  page,
  request,
}) => {
  await enter(page, await demo(request));
  await page.goto('/teacher/overview');
  await page.getByRole('link', { name: 'Class insights', exact: true }).click();
  await expect(page.locator('main h1')).toBeFocused();
  await page.getByRole('link', { name: 'Class progress', exact: true }).click();
  await expect(page.locator('main h1')).toBeFocused();
  await page.goBack();
  await expect(page).toHaveURL(/insights/);
  await expect(page.locator('main h1')).toBeFocused();
  await page.goForward();
  await expect(page).toHaveURL(/progress/);
  await expect(page.locator('main h1')).toHaveCount(1);
  await expect(page.locator('main')).toHaveCount(1);
});

test('refresh failures retain previously loaded progress and expose a retry', async ({
  page,
  request,
}) => {
  await enter(page, await demo(request));
  await page.goto('/teacher/progress');
  await expect(
    page.getByRole('heading', { name: 'Observed class progress', exact: true }),
  ).toBeVisible();
  await page.route('**/classes/*/progress', (r) =>
    r.fulfill({
      status: 503,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'Temporarily unavailable' }),
    }),
  );
  await page.getByRole('button', { name: 'Refresh', exact: true }).click();
  await expect(page.locator('.score-comparison')).toBeVisible();
  await expect(page.getByRole('alert')).toContainText('last loaded data');
  await page.unroute('**/classes/*/progress');
  await page.getByRole('button', { name: 'Try again', exact: true }).click();
  await expect(page.getByRole('alert')).toHaveCount(0);
});

async function prepareGroups(request, s) {
  for (let i = 0; i < 4; i++) {
    const r = await request.post(`/api/classes/${s.classId}/diagnose`);
    expect(r.ok()).toBeTruthy();
    if (!(await r.json()).remaining_pending) break;
  }
  const r = await request.post(`/api/classes/${s.classId}/groups/generate`);
  expect(r.ok()).toBeTruthy();
  return request.get(`/api/classes/${s.classId}/groups`).then((r) => r.json());
}
test('evidence and group review preserve backend state, confirmation is required before assigning', async ({
  page,
  request,
}) => {
  const s = await demo(request);
  const groups = await prepareGroups(request, s);
  expect(groups.length).toBeGreaterThan(0);
  await enter(page, s);
  await page.goto('/teacher/insights');
  const evidence = page
    .getByRole('button', { name: /View evidence for/ })
    .first();
  await evidence.click();
  const drawer = page.getByRole('dialog', {
    name: 'Diagnosis evidence',
    exact: true,
  });
  await expect(drawer).toContainText('Supporting quote');
  await page.keyboard.press('Escape');
  await expect(evidence).toBeFocused();
  await page.goto('/teacher/interventions#groups');
  await page
    .getByRole('button', { name: 'View members', exact: true })
    .first()
    .click();
  await expect(
    page.getByRole('dialog', { name: 'Group members', exact: true }),
  ).toBeVisible();
  await page.keyboard.press('Escape');
  const card = page
    .locator('.group-card')
    .filter({ hasText: groups[0].name })
    .first();
  if (groups[0].review_status === 'proposed') {
    await card.getByRole('button', { name: 'Approve', exact: true }).click();
    await expect(card.getByText('Approved', { exact: true })).toBeVisible();
  }
  await card
    .getByRole('button', {
      name: 'Generate and assign intervention',
      exact: true,
    })
    .click();
  const confirm = page.getByRole('dialog', {
    name: 'Generate for this group?',
    exact: true,
  });
  await expect(confirm).toBeVisible();
  await confirm.getByRole('button', { name: 'Cancel', exact: true }).click();
  await expect(confirm).not.toBeVisible();
  const before = await request
    .get(`/api/classes/${s.classId}/intervention-assignments`)
    .then((r) => r.json());
  await card
    .getByRole('button', {
      name: 'Generate and assign intervention',
      exact: true,
    })
    .click();
  await confirm
    .getByRole('button', {
      name: 'Generate and assign intervention',
      exact: true,
    })
    .click();
  await expect(page.locator('.generated-intervention')).toContainText(
    'educator review',
  );
  const after = await request
    .get(`/api/classes/${s.classId}/intervention-assignments`)
    .then((r) => r.json());
  expect(after.length).toBeGreaterThanOrEqual(before.length);
});

test('student practice, completion and reassessment keep real scores and answers', async ({
  page,
  request,
}) => {
  const teacher = await demo(request);
  const groups = await prepareGroups(request, teacher);
  const group = groups[0];
  await request.patch(`/api/groups/${group.id}/review`, {
    data: { status: 'approved' },
  });
  const generated = await request.post(
    `/api/groups/${group.id}/interventions/generate`,
  );
  expect(generated.ok()).toBeTruthy();
  const assignments = await request
    .get(`/api/classes/${teacher.classId}/intervention-assignments`)
    .then((r) => r.json());
  const assignment =
    assignments.find((a) => a.status !== 'completed') || assignments[0];
  const roster = await request
    .get(`/api/demo/classes/${teacher.classId}/students`)
    .then((r) => r.json());
  const student = roster.find(
    (s) =>
      s.student_id === assignment.student_id ||
      s.student_code === assignment.student_code,
  );
  const s = {
    ...teacher,
    role: 'student',
    studentId: student.student_id,
    studentCode: student.student_code,
  };
  await enter(page, s);
  await page.goto(`/student/interventions/${assignment.assignment_id}`);
  await page.getByRole('tab', { name: 'Try it', exact: true }).click();
  const input = page.locator('input[id^="practice-"]');
  const next = page.getByRole('button', { name: 'Next question', exact: true });
  if (await input.isEnabled()) {
    await input.fill('1');
    while (await next.count()) {
      await next.click();
      await input.fill('1');
    }
    await page
      .getByRole('button', { name: 'Check practice answers', exact: true })
      .click();
  }
  await page
    .getByRole('tab', { name: 'Finish & reassess', exact: true })
    .click();
  const complete = page.getByRole('button', {
    name: 'Finish activity and start reassessment',
    exact: true,
  });
  if (await complete.count()) await complete.click();
  await expect(page.locator('.reassessment-panel')).toBeVisible();
  const reassessment = page.locator('input[id^="reassessment-"]:enabled');
  if (await reassessment.count()) {
    await reassessment.fill('1');
    while (await next.count()) {
      await next.click();
      await reassessment.fill('1');
    }
    await page
      .getByRole('button', { name: 'Submit check-in', exact: true })
      .click();
  }
  await expect(page.locator('.result-summary')).toBeVisible();
  const progress = await request
    .get(`/api/students/${s.studentId}/progress`, {
      headers: { 'X-Student-ID': s.studentId },
    })
    .then((r) => r.json());
  expect(progress.completed_reassessments).toBeGreaterThan(0);
  await page.reload();
  await page
    .getByRole('tab', { name: 'Finish & reassess', exact: true })
    .click();
  await expect(page.locator('.result-summary')).toBeVisible();
});

test('Copilot closes and reopens without losing the conversation or sending during composition', async ({
  page,
  request,
}) => {
  await enter(page, await demo(request));
  await page.goto('/teacher/overview');
  const trigger = page.getByRole('button', {
    name: 'Open Teacher Copilot',
    exact: true,
  });
  await trigger.click();
  const dialog = page.getByRole('dialog', {
    name: 'Teacher Copilot',
    exact: true,
  });
  await expect(dialog).toBeVisible();
  const input = page.getByLabel('Message Teacher Copilot', { exact: true });
  await expect(input).toBeEnabled();
  await input.fill('Summarize this class');
  await input.dispatchEvent('keydown', { key: 'Enter', isComposing: true });
  await expect(input).toHaveValue('Summarize this class');
  await page.getByRole('button', { name: 'Send message', exact: true }).click();
  await expect(page.locator('.copilot-message-user')).toContainText(
    'Summarize this class',
  );
  await expect(page.locator('.copilot-provider-line')).toContainText('Mock');
  await page
    .getByRole('button', { name: 'Close Teacher Copilot', exact: true })
    .click();
  await expect(dialog).not.toBeVisible();
  await expect(trigger).toBeFocused();
  await trigger.click();
  await expect(page.locator('.copilot-message-user')).toContainText(
    'Summarize this class',
  );
});

for (const [name, capabilities, lite] of [
  ['Save Data', { saveData: true }, true],
  ['3G', { effectiveType: '3g' }, true],
  ['low memory', { memory: 4 }, true],
  ['four cores', { cores: 4 }, true],
  ['unknown APIs', {}, false],
])
  test(`automatic effects adapts to ${name}`, async ({ page }) => {
    await page.addInitScript((c) => {
      localStorage.removeItem('classpulse-effects');
      Object.defineProperty(navigator, 'hardwareConcurrency', {
        get: () => c.cores,
        configurable: true,
      });
      Object.defineProperty(navigator, 'deviceMemory', {
        get: () => c.memory,
        configurable: true,
      });
      Object.defineProperty(navigator, 'connection', {
        get: () => ({
          saveData: c.saveData,
          effectiveType: c.effectiveType,
          addEventListener() {},
          removeEventListener() {},
        }),
        configurable: true,
      });
    }, capabilities);
    await page.goto('/login');
    await expect(page.locator('html')).toHaveAttribute(
      'data-effects',
      lite ? 'lite' : 'full',
    );
  });

test('teacher and student role entry use the real catalog and server student resolution', async ({
  page,
  request,
}) => {
  const session = await demo(request, 'student');
  await page.goto('/login');
  await page.getByRole('button', { name: /Teacher/ }).click();
  await page
    .getByLabel('Choose subject', { exact: true })
    .selectOption('Mathematics');
  await page
    .getByLabel('Choose topic', { exact: true })
    .selectOption('Fractions');
  await page
    .getByLabel('Choose class', { exact: true })
    .selectOption(session.classId);
  await page.getByRole('button', { name: /Open teacher dashboard/ }).click();
  await expect(page).toHaveURL(/teacher\/overview/);
  await page.getByRole('button', { name: 'Exit demo', exact: true }).click();
  await page.getByRole('button', { name: /Student/ }).click();
  await page
    .getByLabel('Choose subject', { exact: true })
    .selectOption('Mathematics');
  await page
    .getByLabel('Choose topic', { exact: true })
    .selectOption('Fractions');
  await page
    .getByLabel('Choose class', { exact: true })
    .selectOption(session.classId);
  await page
    .getByLabel('Student code', { exact: true })
    .fill(session.studentCode);
  await page.getByRole('button', { name: /Continue as student/ }).click();
  await expect(page).toHaveURL(/student\/dashboard/);
});

test('role guards preserve redirects and the existing deep links', async ({
  page,
  request,
  browser,
}) => {
  await page.goto('/teacher/overview');
  await expect(page).toHaveURL(/login/);
  const teacher = await demo(request);
  await enter(page, teacher);
  await page.goto('/student/assessment');
  await expect(page).toHaveURL(/teacher\/overview/);
  await expect(
    page.getByRole('status').filter({ hasText: 'student' }),
  ).toBeVisible();
  const context = await browser.newContext();
  const studentPage = await context.newPage();
  await enter(studentPage, await demo(request, 'student'));
  await studentPage.goto('/teacher/insights');
  await expect(studentPage).toHaveURL(/student\/dashboard/);
  await studentPage.goto('/student/interventions');
  await expect(studentPage).toHaveURL(/student\/interventions/);
  await context.close();
});

test('Copilot language changes retain its conversation and input', async ({
  page,
  request,
}) => {
  await enter(page, await demo(request));
  await page.goto('/teacher/overview');
  await page
    .getByRole('button', { name: 'Open Teacher Copilot', exact: true })
    .click();
  const input = page.locator('#copilot-message');
  await expect(input).toBeEnabled();
  await input.fill('Keep this unfinished message');
  await page.locator('.copilot-language-control select').selectOption('te');
  await expect(input).toHaveValue('Keep this unfinished message');
  await expect(page.locator('#copilot-title')).toHaveText('ఉపాధ్యాయ సహాయకుడు');
  await page.locator('.copilot-language-control select').selectOption('hi');
  await expect(input).toHaveValue('Keep this unfinished message');
  await expect(page.locator('#copilot-title')).toHaveText('शिक्षक सहायक');
});
