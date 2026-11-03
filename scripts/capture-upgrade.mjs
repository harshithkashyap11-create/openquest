import { chromium } from '../frontend/node_modules/playwright/index.mjs';
import fs from 'node:fs';
const base = process.argv[2] || 'http://127.0.0.1:5178';
const out = process.argv[3] || 'docs/upgrade-evidence/final';
fs.mkdirSync(out, { recursive: true });
const b = await chromium.launch({ headless: true });
const results = [],
  errors = [];
const classes = await fetch(base + '/api/demo/classes').then((r) => r.json());
const c = classes.find((x) => x.topic === 'Fractions') || classes[0];
const roster = await fetch(`${base}/api/demo/classes/${c.id}/students`).then(
  (r) => r.json(),
);
const assignments = await fetch(
  `${base}/api/classes/${c.id}/intervention-assignments`,
).then((r) => r.json());
const a =
  assignments.find((x) => x.reassessment_total_questions > 0) || assignments[0];
const learner =
  roster.find(
    (x) => x.student_id === a?.student_id || x.student_code === a?.student_code,
  ) || roster[0];
const session = {
  classId: c.id,
  className: c.class_name,
  subject: c.subject,
  topic: c.topic,
  studentId: learner.student_id,
  studentCode: learner.student_code,
};
for (const lang of ['en', 'hi', 'te'])
  for (const width of [360, 414, 768, 1024, 1440]) {
    const ctx = await b.newContext({
      viewport: { width, height: width < 768 ? 780 : 800 },
    });
    await ctx.addInitScript(
      ({ lang, session }) => {
        localStorage.setItem('classpulse.language', lang);
        localStorage.setItem('classpulse-effects', 'full');
        sessionStorage.setItem(
          'classpulse.demo-session',
          JSON.stringify({
            ...session,
            role: location.pathname.startsWith('/teacher')
              ? 'teacher'
              : 'student',
          }),
        );
      },
      { lang, session },
    );
    const p = await ctx.newPage();
    p.on('pageerror', (e) => errors.push(e.message));
    const routes = [
      ['entry', '/login'],
      ['teacher', '/teacher/overview'],
      ['insights', '/teacher/insights'],
      ['groups', '/teacher/interventions#groups'],
      ['class-progress', '/teacher/progress'],
      ['teacher-quizzes', '/teacher/quizzes'],
      ['student', '/student/dashboard'],
      ['assessment', '/student/assessment'],
      ['assignments', '/student/interventions'],
      ['student-progress', '/student/progress'],
      ['student-quizzes', '/student/quizzes'],
      ...(a ? [['activity', `/student/interventions/${a.assignment_id}`]] : []),
    ];
    for (const [name, route] of routes) {
      await p.goto(base + route);
      await p.waitForLoadState('networkidle');
      await p.locator('h1').waitFor();
      // Let finite presentation animations settle without adding application delays.
      await p.evaluate(() =>
        Promise.all(
          document
            .getAnimations()
            .filter((a) => a.effect?.getTiming().iterations !== Infinity)
            .map((a) => a.finished.catch(() => {})),
        ),
      );
      const layout = await p.evaluate(() => ({
        overflow: document.documentElement.scrollWidth > innerWidth + 1,
        headingCount: document.querySelectorAll('main h1').length,
        mainCount: document.querySelectorAll('main').length,
        smallTargets: [
          ...document.querySelectorAll('button,select,a[href],summary'),
        ]
          .filter(
            (el) =>
              el.getClientRects().length &&
              !el.closest('[hidden],dialog:not([open])') &&
              (el.getBoundingClientRect().height < 43.5 ||
                el.getBoundingClientRect().width < 43.5),
          )
          .map((el) => ({
            tag: el.tagName,
            text: el.textContent.trim().slice(0, 60),
            w: Math.round(el.getBoundingClientRect().width),
            h: Math.round(el.getBoundingClientRect().height),
          })),
      }));
      results.push({ name, lang, width, ...layout });
      if ([360, 768, 1440].includes(width))
        await p.screenshot({
          path: `${out}/${name}-${lang}-${width}.png`,
          fullPage: true,
        });
      await p.evaluate(
        () => (document.documentElement.style.fontSize = '200%'),
      );
      results.push({
        name: name + '-text-zoom',
        lang,
        width,
        overflow: await p.evaluate(
          () => document.documentElement.scrollWidth > innerWidth + 1,
        ),
      });
      await p.evaluate(() => (document.documentElement.style.fontSize = ''));
      if (name === 'activity') {
        await p.getByRole('tab').last().click();
        await p.evaluate(() =>
          Promise.all(
            document
              .getAnimations()
              .filter((a) => a.effect?.getTiming().iterations !== Infinity)
              .map((a) => a.finished.catch(() => {})),
          ),
        );
        if ([360, 1440].includes(width))
          await p.screenshot({
            path: `${out}/reassessment-${lang}-${width}.png`,
            fullPage: true,
          });
      }
    }
    await p.goto(base + '/teacher/overview');
    await p.waitForLoadState('networkidle');
    await p.locator('.copilot-launch').click();
    await p.locator('dialog.copilot-panel[open]').waitFor();
    await p.waitForLoadState('networkidle');
    if ([360, 768, 1440].includes(width))
      await p.screenshot({
        path: `${out}/copilot-${lang}-${width}.png`,
        fullPage: true,
      });
    await p.keyboard.press('Escape');
    // Text zoom, independent from viewport-size coverage.
    await p.goto(base + '/login');
    await p.waitForLoadState('networkidle');
    await p.evaluate(() => (document.documentElement.style.fontSize = '200%'));
    results.push({
      name: 'entry-text-zoom',
      lang,
      width,
      overflow: await p.evaluate(
        () => document.documentElement.scrollWidth > innerWidth + 1,
      ),
    });
    await ctx.close();
    console.log(`Captured ${lang} at ${width}px`);
  }
fs.writeFileSync(out + '/layout.json', JSON.stringify(results, null, 2));
fs.writeFileSync(out + '/console-errors.json', JSON.stringify(errors, null, 2));
console.log(
  JSON.stringify(
    {
      screens: results.length,
      overflow: results
        .filter((x) => x.overflow)
        .map((x) => ({ name: x.name, lang: x.lang, width: x.width })),
      smallTargets: results
        .filter((x) => x.smallTargets?.length)
        .map((x) => ({
          name: x.name,
          lang: x.lang,
          width: x.width,
          targets: x.smallTargets,
        })),
      errors,
    },
    null,
    2,
  ),
);
if (results.some(result => result.overflow || result.headingCount === 0 || result.mainCount === 0 || result.smallTargets?.length) || errors.length) process.exitCode = 1;
await b.close();
