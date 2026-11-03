import { expect, test } from '@playwright/test';

async function sessionFor(request) {
  const classes = await request.get('/api/demo/classes').then((r) => r.json());
  const c = classes.find((item) => item.topic === 'Fractions');
  const roster = await request
    .get(`/api/demo/classes/${c.id}/students`)
    .then((r) => r.json());
  return {
    teacher: {
      role: 'teacher',
      classId: c.id,
      className: c.class_name,
      subject: c.subject,
      topic: c.topic,
    },
    student: {
      role: 'student',
      classId: c.id,
      className: c.class_name,
      subject: c.subject,
      topic: c.topic,
      studentId: roster[0].student_id,
      studentCode: roster[0].student_code,
    },
  };
}

async function signIn(context, session) {
  await context.addInitScript(
    (value) =>
      sessionStorage.setItem('classpulse.demo-session', JSON.stringify(value)),
    session,
  );
}

test('teacher publication, student reflection and repair, live evidence, reviewed lesson', async ({
  page,
  browser,
  request,
}, testInfo) => {
  const sessions = await sessionFor(request);
  await signIn(page.context(), sessions.teacher);
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.goto('/teacher/quizzes');
  await expect(
    page.getByRole('heading', { name: 'Quizzes', exact: true }),
  ).toBeVisible();
  await page.getByRole('button', { name: 'Create quiz', exact: true }).click();
  await page.getByRole('button', { name: 'Load fractions example' }).click();
  await expect(
    page.getByText('5 questions imported.', { exact: false }),
  ).toBeVisible();
  await page
    .getByLabel('Quiz title', { exact: true })
    .fill('Fractions browser checkpoint');
  await page.getByRole('button', { name: 'Save draft', exact: true }).click();
  await page.getByRole('button', { name: 'Publish quiz', exact: true }).click();
  await expect(page.getByText('Published quiz', { exact: true })).toBeVisible();
  await expect(page.getByText('0 / 40', { exact: true })).toBeVisible();

  const context = await browser.newContext();
  await signIn(context, sessions.student);
  const learner = await context.newPage();
  learner.on('pageerror', (error) => errors.push(error.message));
  await learner.goto('/student/quizzes');
  await learner
    .getByRole('link', { name: 'Fractions browser checkpoint', exact: true })
    .click();
  await expect(
    learner.getByRole('button', { name: 'Submit quiz', exact: true }),
  ).toBeDisabled();
  for (const fieldset of await learner.locator('fieldset.quiz-question').all())
    await fieldset.getByRole('radio').first().check();
  await learner
    .getByRole('button', { name: 'Submit quiz', exact: true })
    .click();
  await expect(
    learner.getByRole('heading', { name: 'Your result', exact: true }),
  ).toBeVisible();
  await learner
    .getByRole('button', { name: 'Reflect on question 1', exact: true })
    .click();
  await expect(
    learner.getByRole('heading', { name: 'Let’s understand it', exact: true }),
  ).toBeFocused();
  await learner
    .getByLabel('Explain your thinking', { exact: true })
    .fill('I added the numerators and denominators together.');
  await learner
    .getByRole('button', { name: 'Send explanation', exact: true })
    .click();
  await expect(
    learner.getByText('Template feedback', { exact: true }),
  ).toBeVisible();
  await learner.getByRole('radio', { name: 'B. 3/4', exact: true }).check();
  await learner
    .getByRole('button', { name: 'Check repair answer', exact: true })
    .click();
  await expect(
    learner.getByText('Repair answer correct', { exact: true }),
  ).toBeVisible();
  await learner.reload();
  await learner
    .getByRole('button', { name: 'Reflect on question 1', exact: true })
    .click();
  await expect(
    learner.getByText('Repair answer correct', { exact: true }),
  ).toBeVisible();
  await learner.setViewportSize({ width: 390, height: 844 });
  await learner.evaluate(() => window.scrollTo(0, 0));
  expect(
    await learner.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await learner.screenshot({
    path: testInfo.outputPath('student-mobile.png'),
    fullPage: true,
  });
  await learner.getByLabel('Language', { exact: true }).selectOption('hi');
  await expect(
    learner.getByRole('heading', { name: 'आइए इसे समझें', exact: true }),
  ).toBeVisible();

  // The already-open report must update without navigation or reload.
  await page.bringToFront();
  await expect(page.getByText('1 / 40', { exact: true })).toBeVisible();
  await page.getByText('Student evidence', { exact: true }).first().click();
  await expect(
    page.getByText('I added the numerators and denominators together.', {
      exact: true,
    }),
  ).toBeVisible();
  await page
    .getByRole('button', { name: 'Flag interpretation', exact: true })
    .first()
    .click();
  await expect(
    page.getByRole('button', { name: 'Restore interpretation', exact: true }),
  ).toBeVisible();
  await page
    .getByRole('button', { name: 'Suggest next lesson', exact: true })
    .click();
  await page
    .getByLabel('Lesson suggestion', { exact: true })
    .fill('Use fraction strips in pairs for five minutes.');
  await page
    .getByRole('button', { name: 'Accept lesson', exact: true })
    .click();
  await expect(
    page.getByText('Lesson accepted', { exact: true }),
  ).toBeVisible();
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({
    path: testInfo.outputPath('teacher-evidence.png'),
    fullPage: true,
  });
  expect(errors).toEqual([]);
  await context.close();
});

test('invalid CSV reports its row and keeps the existing draft', async ({
  page,
  request,
}) => {
  const sessions = await sessionFor(request);
  await signIn(page.context(), sessions.teacher);
  await page.goto('/teacher/quizzes');
  await page.getByRole('button', { name: 'Create quiz', exact: true }).click();
  await page.getByLabel('Quiz title', { exact: true }).fill('Keep my draft');
  await page.getByLabel('Upload quiz CSV', { exact: true }).setInputFiles({
    name: 'invalid.csv',
    mimeType: 'text/csv',
    buffer: Buffer.from(
      'question,option_a,option_b,option_c,option_d,correct_option,explanation\nQuestion,A,B,C,D,Z,Explanation\n',
    ),
  });
  await expect(page.getByRole('alert')).toContainText('Row 2');
  await expect(page.getByLabel('Quiz title', { exact: true })).toHaveValue(
    'Keep my draft',
  );
});

test('AI outage preserves explanation and allows a retry without losing the grade', async ({
  page,
  request,
}) => {
  const sessions = await sessionFor(request);
  const headers = {
    'X-Demo-Role': 'teacher',
    'X-Class-ID': sessions.teacher.classId,
  };
  const response = await request.post(
    `/api/classes/${sessions.teacher.classId}/quizzes`,
    {
      headers,
      data: {
        title: 'Retry checkpoint',
        questions: [
          {
            text: '1/2 + 1/3?',
            options: ['2/5', '5/6'],
            correct_option: 1,
            explanation: 'Use sixths: 3/6 + 2/6 = 5/6.',
            concept: 'Fractions',
          },
        ],
      },
    },
  );
  expect(response.status()).toBe(201);
  const quiz = await response.json();
  await request.post(`/api/quizzes/${quiz.id}/publish`, { headers });
  await signIn(page.context(), sessions.student);
  await page.goto(`/student/quizzes/${quiz.id}`);
  await page.getByRole('radio').first().check();
  await page.getByRole('button', { name: 'Submit quiz', exact: true }).click();
  await page
    .getByRole('button', { name: 'Reflect on question 1', exact: true })
    .click();
  await page
    .getByLabel('Explain your thinking', { exact: true })
    .fill('I guessed.');
  const pattern = '**/questions/*/reflect';
  await page.route(pattern, (route) =>
    route.fulfill({
      status: 503,
      contentType: 'application/json',
      body: JSON.stringify({
        detail:
          'The AI tutor is unavailable. Your quiz is saved; please retry.',
      }),
    }),
  );
  await page
    .getByRole('button', { name: 'Send explanation', exact: true })
    .click();
  await expect(page.getByRole('alert')).toContainText('Your quiz is saved');
  await expect(
    page.getByLabel('Explain your thinking', { exact: true }),
  ).toHaveValue('I guessed.');
  await page.unroute(pattern);
  await page
    .getByRole('button', { name: 'Send explanation', exact: true })
    .click();
  await expect(
    page.getByText('Template feedback', { exact: true }),
  ).toBeVisible();
  await expect(page.locator('.quiz-result-strip > strong')).toContainText(
    '0 / 1',
  );
});

test('teacher sidebar labels Gemini replies and template fallback distinctly', async ({
  page,
  request,
}) => {
  const sessions = await sessionFor(request);
  await signIn(page.context(), sessions.teacher);
  await page.route('**/copilot/chat', async (route) => {
    const input = route.request().postDataJSON();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        reply: 'Use fraction strips to explain common denominators.',
        intent: 'teaching_assistance',
        subject: 'Mathematics',
        topic: 'Fractions',
        class_id: sessions.teacher.classId,
        class_context_summary: null,
        draft_content: null,
        suggested_followups: [],
        provider: input.message.includes('fallback')
          ? 'gemini_fallback'
          : 'gemini',
        model_version: 'gemini-3.8-flash',
      }),
    });
  });
  await page.goto('/teacher/quizzes');
  const toggle = page.getByRole('button', {
    name: 'Open Teacher Copilot',
    exact: true,
  });
  await expect(toggle).toBeVisible();
  await toggle.click();
  const input = page.getByLabel('Message Teacher Copilot', { exact: true });
  await expect(input).toBeEnabled();
  await input.fill('Explain fractions using strips');
  await page.getByRole('button', { name: 'Send message', exact: true }).click();
  await expect(page.locator('.copilot-provider-line').first()).toContainText(
    'Gemini',
  );
  await expect(
    page.locator('.copilot-provider-line').first(),
  ).not.toContainText('fallback');
  await input.fill('Show fallback feedback');
  await page.getByRole('button', { name: 'Send message', exact: true }).click();
  await expect(page.locator('.copilot-provider-line').last()).toContainText(
    'Gemini template fallback',
  );
});
