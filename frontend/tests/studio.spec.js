import { test, expect } from '@playwright/test';

async function login(page, role, username, password = '*') {
  await page.goto('/login');
  await page.getByRole('button', { name: role, exact: true }).click();
  await page.getByLabel('Username', { exact: true }).fill(username);
  await page.getByLabel('Password', { exact: true }).fill(password);
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'My courses', exact: true })).toBeVisible();
}

test('demo username login opens only assigned courses and student can switch courses', async ({ page }) => {
  await login(page, 'Teacher', 'math1', 'a');
  await expect(page.getByRole('button', { name: /Open Fractions/ })).toBeVisible();
  await expect(page.getByRole('button', { name: /Open Basic algebra/ })).toBeVisible();
  await expect(page.getByRole('button', { name: /Open Force and motion/ })).toHaveCount(0);
  await page.getByRole('button', { name: /Open Fractions/ }).click();
  await expect(page).toHaveURL(/teacher\/overview/);
  await page.getByRole('button', { name: 'Sign out', exact: true }).click();
  await login(page, 'Student', 'student1');
  await page.getByRole('button', { name: /Open Fractions/ }).click();
  await expect(page).toHaveURL(/student\/dashboard/);
  await page.getByRole('link', { name: 'My courses', exact: true }).first().click();
  await page.getByRole('button', { name: /Open Basic algebra/ }).click();
  await expect(page.locator('.topbar-class')).toContainText('Basic algebra');
  await page.reload();
  await expect(page.locator('.topbar-class')).toContainText('Basic algebra');
});

test('teacher publishes library activity, student submits drawing and feedback, teacher exports work', async ({ page, browser }) => {
  await login(page, 'Teacher', 'math1');
  await page.getByRole('button', { name: /Open Fractions/ }).click();
  await page.getByRole('link', { name: 'Classroom Studio', exact: true }).click();
  await page.getByRole('navigation', { name: 'Classroom tools' }).getByRole('button', { name: 'Question library', exact: true }).click();
  await page.getByRole('button', { name: 'Add to draft', exact: true }).first().click();
  await page.getByRole('button', { name: 'Activities', exact: true }).click();
  await page.getByLabel('Activity title', { exact: true }).fill('Studio browser checkpoint');
  await page.getByRole('button', { name: 'Save draft', exact: true }).click();
  await expect(page.getByRole('status')).toContainText('Draft saved');
  await page.getByLabel('Reviewed wording and answer keys').check();
  await page.getByRole('button', { name: 'Publish activity', exact: true }).click();
  await expect(page.getByRole('status')).toContainText('Published');
  const student = await browser.newPage();
  await login(student, 'Student', 'S1');
  await student.getByRole('button', { name: /Open Fractions/ }).click();
  await student.getByRole('link', { name: 'Classroom Studio', exact: true }).click();
  await student.getByRole('button', { name: /Start Studio browser checkpoint/ }).click();
  await student.getByRole('radio').first().check();
  await student.getByLabel('Explain your reasoning', { exact: true }).fill('I added the numerators and denominators.');
  const board = student.getByLabel('Drawing board');
  const box = await board.boundingBox();
  await student.mouse.move(box.x + 20, box.y + 20); await student.mouse.down();
  await student.mouse.move(box.x + 120, box.y + 70); await student.mouse.up();
  await student.getByRole('button', { name: 'Submit activity', exact: true }).click();
  await expect(student.getByText('Saved attempt 1', { exact: true })).toBeVisible();
  await student.getByLabel('Message to tutor').fill('I added the denominators.');
  await student.getByRole('button', { name: 'Get feedback', exact: true }).click();
  await expect(student.getByText('template', { exact: true }).first()).toBeVisible();
  await student.reload();
  await student.getByRole('button', { name: /Start Studio browser checkpoint/ }).click();
  await expect(student.getByText('I added the denominators.', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Reports', exact: true }).click();
  await expect(page.getByText('Studio browser checkpoint', { exact: true })).toBeVisible();
  const download = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Download work PDF', exact: true }).first().click();
  expect((await download).suggestedFilename()).toMatch(/\.pdf$/);
  await student.close();
});

test('QR room creates printable cards and persists manually entered answers', async ({ page }) => {
  await login(page, 'Teacher', 'math1');
  await page.getByRole('button', { name: /Open Fractions/ }).click();
  await page.getByRole('link', { name: 'Classroom Studio', exact: true }).click();
  await page.getByRole('button', { name: 'QR responses', exact: true }).click();
  await page.getByRole('button', { name: 'Prepare response cards', exact: true }).click();
  await expect(page.getByRole('img', { name: /Response card/ }).first()).toBeVisible();
  await page.getByRole('button', { name: 'Hide cards', exact: true }).click();
  await page.getByRole('combobox', { name: 'Choose activity', exact: true }).selectOption({ label: 'Studio browser checkpoint' });
  await page.getByRole('combobox', { name: 'Question', exact: true }).selectOption({ index: 1 });
  await page.getByRole('button', { name: 'Open response session', exact: true }).click();
  await page.getByText('Manual response entry', { exact: true }).click();
  await page.getByLabel('Answer S001', { exact: true }).selectOption('1');
  await expect(page.getByText('1/40 responses · open', { exact: true })).toBeVisible();
  await page.reload();
  await page.getByRole('button', { name: 'QR responses', exact: true }).click();
  await page.getByRole('combobox', { name: 'Resume a response session', exact: true }).selectOption({ index: 1 });
  await expect(page.getByText('1/40 responses · open', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Close response session', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Scan response cards', exact: true })).toBeDisabled();
});

test('native recording saves a playable WebM with student work and fits a narrow screen', async ({ page }) => {
  await page.addInitScript(() => {
    Object.defineProperty(window, 'SpeechRecognition', { value: undefined });
    Object.defineProperty(window, 'webkitSpeechRecognition', { value: undefined });
    navigator.mediaDevices.getUserMedia = async () => {
      const audio = new AudioContext(); const oscillator = audio.createOscillator();
      const destination = audio.createMediaStreamDestination(); oscillator.connect(destination); oscillator.start();
      window.testAudio = audio; return destination.stream;
    };
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await login(page, 'Student', 'S2');
  await page.getByRole('button', { name: 'Open Fractions', exact: true }).click();
  await page.goto('/student/studio');
  await page.getByRole('button', { name: /Start Studio browser checkpoint/ }).click();
  await page.getByRole('radio').first().check();
  await page.getByRole('button', { name: 'Record voice', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Submit activity', exact: true })).toBeDisabled();
  await page.getByRole('button', { name: 'Stop recording', exact: true }).click();
  await expect(page.locator('audio')).toHaveAttribute('src', /^data:audio\/webm;base64,.+/);
  await page.getByLabel('Editable transcript').fill('I compared the denominators.');
  await page.getByRole('button', { name: 'Submit activity', exact: true }).click();
  await expect(page.getByText('Saved attempt 1', { exact: true })).toBeVisible();
  await page.reload();
  await page.getByRole('button', { name: /Start Studio browser checkpoint/ }).click();
  await expect(page.locator('audio').first()).toHaveAttribute('src', /^data:audio\/webm;base64,.+/);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});
