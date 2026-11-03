# ClassPulse Atelier upgrade progress

## Initial repository state — 2026-11-02

- Active app: `openpost/`, discovered inside the open workspace `open quest/` (spec A1 confirmed).
- Branch: `main`; baseline commit: `8fb7d628c6981b0cc3d2da548bb2ea40306825b0`.
- Existing uncommitted changes: backend provider integration and quiz learning loop, frontend routes/shell/Copilot/API/dictionaries/package files; preserved. Full initial status: `/tmp/classpulse-upgrade-baseline/git-status.txt`.
- Safe checkpoint: `/tmp/classpulse-upgrade-baseline/source-checkpoint.tar.gz`, includes source and existing untracked work, excludes secrets, database, dependencies and generated files. Baseline build copied to `/tmp/classpulse-upgrade-baseline/dist`.
- No staging, commits, pushes or deployment. Existing SQLite file untouched.
- Lockfile SHA256: `f9830e2523600b537e6c90b311903cda3ae0c6fcd0df6a0b5576909db2d066e0`.

## Mandatory audit — completed before UI implementation

React 19.3.1, React DOM 19.3.1, React Router DOM 7.18.5, Vite 8.3.5 with plugin-react 6.1.2. npm/package-lock convention. React StrictMode enabled. Global ordinary CSS in `index.css` and `App.css`; Copilot and quizzes have separate stylesheets. No Tailwind, shadcn, CSS framework or animation package. Recharts 3.10.1 for insights; lucide-react 1.66.0 icons. All page imports are lazy. `AppShell` was eager, importing Copilot eagerly, including its rendering helpers on entry.

### Page inventory

| Actual URL / view | Component | Data and state |
|---|---|---|
| `/login`, `/` redirect | `frontend/src/pages/Login.jsx` | demo classes; subject/topic/class from actual catalog; roster; server validates student code |
| `/teacher/overview` | `pages/TeacherDashboard.jsx` | assessment summary, diagnosis summary, progress; diagnosis mutation |
| `/teacher/quizzes` | `pages/TeacherQuizzes.jsx` | quiz authoring/CSV/review/publication/live evidence/lesson review (pre-existing user work) |
| `/teacher/insights` | `pages/ClassInsights.jsx` | diagnoses, assessment summary, student filter, confidence/evidence/provider |
| `/teacher/interventions#groups` | `pages/Intervention.jsx`: TeacherInterventions | groups generation, approval/rejection, real members |
| `/teacher/interventions#assignments` | same component | intervention generation also creates assignments in existing backend; no separate approval endpoint |
| `/teacher/progress` | `pages/ClassProgress.jsx` | backend aggregated scores, sample counts, support queue |
| `/student/dashboard` | `pages/StudentDashboard.jsx` | student-scoped assessment and assignments |
| `/student/quizzes`, `/:quizId` | `pages/StudentQuizzes.jsx` | publication list, answers, reflection, repair; student header |
| `/student/assessment` | `pages/Assessment.jsx` | class questions, local answers/explanations, batch submission |
| `/student/interventions` | `pages/Intervention.jsx`: StudentActivityList | student-scoped assignments |
| `/student/interventions/:assignmentId` | same: StudentActivity | learn/example/practice/completion/reassessment embedded states |
| `/student/progress` | `pages/StudentProgress.jsx` | student-scoped scores and samples |
| unmatched | `pages/NotFound.jsx` | functional return link |
| teacher assistant | `components/TeacherCopilot.jsx` | `/copilot/chat`, `/copilot/classes/:id/context`, taxonomy, demo classes; context-key guarded conversation |

RoleRoute preserves role separation and existing URL parameters/hashes. Sessions use `classpulse.demo-session` in sessionStorage, with class/subject/topic and student ID/code. Demo access is explicitly not production authentication. Language uses `classpulse.language` localStorage; `I18nProvider` updates html lang without remounting forms. 275 keys per locale at baseline. Copilot and teacher quiz authoring contain pre-existing hardcoded English UI strings; localize as part of page polish rather than claiming original parity means full coverage.

### Component / API inventory

Reusable: AppShell, LanguageSelector, PageHeader (focusable h1), MetricCard, LoadingState/ErrorState/EmptyState, useAsyncData, existing CSS buttons/panels/status pills. Duplicates: Score function on three pages, multiple control/badge styles, Copilot drawer and student reflection sidebar. No shared dialog primitive, effects preference, toast system, error boundary or question transition. Existing inline live status messages are preferable to disruptive temporary toasts.

`services/api.js`: Axios, normalized /api base URL, student identity header, request error extraction. `classpulseApi.js`: demo, assessment, diagnosis pagination, groups/review, generation, assignments/practice/completion/reassessment/progress, Copilot. `quizApi.js`: existing teacher/class and student-scoped quiz requests. No API contract changes planned. All analytical pages require live backend; no fabricated activity feed. Taxonomy has Mathematics/Fractions/Basic algebra, Science/Force and motion/Basic electricity, English/Grammar/Subject-verb agreement, confirmed from backend catalog.

### Token, motion and asset inventory

Existing tokens: ink #20283a, muted #788196, line #e7eaf1, surface white, canvas #f5f7fb, primary #4656c9, primary-soft #eef0ff; status colors and radius14/shadow; many literal colors override them. Spacing is ad hoc (9/13/17/21/22/26/34/38px). Breakpoints 1080/760/540px; Copilot compact at1100px. Motion: button/nav140ms, bars animate width180ms, spinner1.4s; Copilot width/flex180ms, enter170ms, pending pulse900ms, mobile translate200ms. Only CSS reduced-motion overrides; JS smooth scroll ignores preference. No effects setting. Font stacks name Manrope/DM Sans without loading them; system fallback used, no downloads. Linux has Noto Sans Devanagari and Telugu. No external font CDN or tracker. Unused hero.png exists; no need to load it.

PWA discrepancy: no web manifest, service worker file, registration or installability exists in active frontend. Preserve absence; do not invent offline submission. Network failures already show retry states. No classroom API caching introduced.

### What Feels Cheap Today

| Severity | Concrete observation | Measurable improvement |
|---|---|---|
| high | App.css muted labels #939bad on white | text >=4.5:1, semantic secondary token |
| high | 1440px dashboard: open386px Copilot squeezes five metric columns | default closed assistant; max four columns with >=160px cards |
| high | mobile sidebar becomes horizontally scrolling row | modal menu below 768px, every route discoverable |
| high | language/select/buttons several targets below44px | 44px shared controls,48px principal student actions |
| high | AppShell focuses h1 on language changes | route-only heading focus; language retains control focus |
| medium | entry hero only says choose a role, no learning loop | concise Diagnose → Group → Intervene → Reassess composition |
| medium | five small metrics with low hierarchy | tabular28px values, stronger icons/labels |
| medium | ClassInsights long nested diagnosis cards and680px nested scroller | compact records + evidence drawer + accessible filters |
| medium | progress scores have no proportional visual scale | comparison bars fixed0–100, samples and non-causal note retained |
| medium | Assessment renders all questions equally | question focus with previous/next, answer state outside motion |
| medium | mobile signout is hidden in sidebar-bottom | include signout in mobile drawer |
| medium | Copilot animates layout width/flex-basis | fixed overlay,transform/opacity only |
| medium | Copilot/quiz authoring hardcoded English | preserve identifiers; translate UI across locales |
| low | uppercase tracking applied to translated labels | no tracking/uppercase in Hindi/Telugu |

Strengths retained: lazy routes and role guards; provenance/confidence/follow-up distinctions; server-confirmed mutations and accurate samples; synthetic demo labeling; student-header isolation; context-key request guards. Minimum architecture changes: effects provider, single route entrance wrapper (no duplicate exiting trees), native-dialog overlay shared by drawer/modal/evidence, shared question pager, reuse existing CSS class APIs and Score consolidation. Motion library not needed for these transforms: browser WAAPI/CSS avoids runtime cost and extra framework. Presets include reference spring metadata but no spring physics dependency. Native View Transitions and shared-element morphs deferred, preserving immediate routes and focus.

### Baseline executable checks

| Check | Command | Result |
|---|---|---|
| Build | `cd frontend && npm run build` | PASS, exit0, Vite1.58s |
| Lint | `npm run lint` | PASS, exit0 |
| Translation parity | `npm run i18n:check` | PASS,275 keys each |
| Existing browser tests | `npm run test:e2e` | PASS,4/4,21.1s; expected503 outage test logs request failure |
| Backend | `cd backend && python3 -m pytest -q` | PASS,137 passed,1 skipped,1 Starlette/httpx deprecation warning |
| Initial responsive evidence | browser Chromium | 27 screenshots entry/teacher/student ×en/hi/te ×360/768/1440;800px desktop/780px mobile |
| Keyboard/reduced motion | Chromium | Tab entry control reachable; reduced media applied; only CSS respects it at baseline |
| Lighthouse/4xCPU/Slow3G | production baseline profiling | PASS, Entry98/95/100; Slow3G LCP4340ms,CLS0; JSON retained |
| Screen reader | Orca/NVDA | NOT TESTED; no session available |

Bundle output: main JS128.57KB gzip; ClassInsights105.15KB gzip; teacher quiz4.99KB; intervention3.87KB; shared jsx-runtime3.46KB. Main CSS9.26KB gzip, quiz CSS2.02KB. Font transfer0. Exact bytes in `docs/upgrade-evidence/baseline/bundles.json`. These are asset sizes, not observed compressed HTTP transfer. Vite dev server does not serve gzip; record transfer separately using production network resource set and local gzip.

Port8000 belongs to another service (health200 but demo/classes404). Verification uses existing disposable test harness on 8012 with mock provider, real SQLite persistence and imported labeled synthetic data. Live AI provider invocation deliberately not required. No original database reset or rewrite.

## Ordered implementation plan

| Phase | Files | Gate |
|---|---|---|
| A | styles/tokens.css, index.css, motion/presets.js, hooks/useLiteEffects.js, context/EffectsProvider.jsx, App.jsx | contrast, preference tests, build/lint/i18n |
| B | AppShell.jsx, motion/RouteTransition.jsx, hooks/useModalDialog.js, ui/MobileDrawer.jsx, shell styles | mobile focus/Escape,history,role paths |
| C | ui/Button/Card/StatusPill/Tabs/ProgressBar/QuestionPager, MetricCard/PageStates/PageHeader | keyboard/form state; existing browser suite |
| D | Login, TeacherDashboard, ClassInsights, Intervention, ClassProgress, TeacherCopilot, StudentDashboard, Assessment, StudentProgress, quiz pages/styles | original workflows against disposable backend; each page screenshot |
| E | shared/presentation CSS, code-splitting, effects | budget, CPU/network, all capability branches |
| F | browser tests, evidence, measurement script, docs/three-minute-demo.md | final regression/diff/report/checklist |

## Phase log

Audit: PASS — source read and baseline checks completed before interface changes. All subsequent evidence must distinguish actual backend records from provider stubs used only in isolated tests.

Phase A: PASS — token stylesheet imported once; compatibility aliases retain existing classes. Effects provider centralizes capability/storage listeners. Build/lint/i18n exit0. Programmatic contrast results in evidence/contrast.json; stronger control border #75888F selected for>=3:1. No runtime dependencies or fonts added (system Noto script coverage verified). Application shell and Copilot now split from entry. Baseline Lighthouse:98 performance,95 accessibility,100 best practices. Baseline 4xCPU Slow3G lab measured in baseline/performance.json. Four new browser regression tests failed before implementation: missing effects control, missing mobile drawer, multi-question answer ambiguity, route focus failure.

Phase B: PASS — on-demand lazy Copilot trigger; persistent desktop collapse; mobile native-dialog menu; one mounted route with interruptible WAAPI entrance, route-only heading focus, history scroll map, no overlapping trees. 3/3 focused browser tests passed (Lite/reduced override/persistence/language focus; mobile Tab/Escape/focus return/navigation; route Back/Forward). Fixed a real layout overflow from wrapping a column flex header and delayed data-arrival focus stealing from an already-used selector. Native dialog supplemented with explicit Tab-edge cycling. Lint exit0 with no warnings. Checkpoint: `/tmp/classpulse-upgrade-baseline/phase-b-source`.

Phase C: PASS — shared Button variants, Card, StatusPill, ScoreCard/ProgressBar, Tabs, QuestionPager/QuestionTransition, modal/drawer foundation. Existing MetricCard now uses exact localized final values with screen-reader-stable labels; only integer counts animate once. Three duplicate Score renderers consolidated without losing samples. 44px controls,48px student answer controls; no layout property animation on bars. Native inline live notifications retained instead of adding a duplicate toast system. Build/lint/i18n passed (310 locale keys); previously passing shell tests preserved. Question and tab interactions are exercised during Phase D integration. Optional completion ring omitted where it would duplicate readable counts. Checkpoint: `/tmp/classpulse-upgrade-baseline/phase-c-source`.

Phase D: PASS (initial integration) — Entry rebuilt around the actual learning loop and catalog; teacher overview prioritizes four metrics and next action with real group previews; Class Insights has compact records, keyboard tabs, an evidence dialog and a numeric alternative to the chart; group filters/member drawer and explicit generate-and-assign confirmation; shared zero-baseline progress comparisons; student questions and intervention stages use the same answer-preserving pager; Copilot is a lazy modal with conversation retained on dismissal and IME-safe send. Existing quiz authoring/CSV/report/reflection/repair screens integrated and localized. Initial combined run:11/12 passed; the provider-label test skipped opening the lazy-mounted assistant because its immediate count() raced the shell load. Updated that interaction to await the visible on-demand launcher; provenance assertions remain unchanged. Re-run required before release. Eight new behavior tests passed against the disposable API. Build/lint/i18n pass. No backend source or API client changes in this upgrade. Current per-locale keys498, with original 275 keys/values preserved.

Discrepancies resolved: diagnosis API does not include full student responses, so drawer labels the exact supporting quote and explains the API limit; no invented full-response content. Generation creates assignments as an existing atomic server operation; explicit confirmation preserves teacher control without inventing a draft approval endpoint. Native dialog default geometry is modal on desktop and mobile to keep all data visible beneath a stable workspace. Dark-mode UI, native View Transitions and shared-element morphs are deferred optional embellishments; light-theme foundations and the core workflows take priority. No offline-shell capability existed to preserve. Full generated teaching text remains in the backend-provided language; UI labels support all three locales.

Phase E: PASS — no new runtime/development dependencies; no external font or tracking requests. Entry asset set is measured independently from route chunks. Save Data,3G,4GB memory,4-core and unknown-capability branches passed browser tests; reduced motion overrides manual Full. All original 275 translation values per locale remain unchanged;498 keys now match. Three text-zoom grid overflows were reproduced and corrected using minmax(0,1fr), min-width:0 and grapheme-safe wrapping. Logo touch area expanded to 44px. Sidebar and tab selected backgrounds share a transform-only moving indicator that observes translated label geometry; ordinary refetches do not replay route motion. Initial lab frame sample at4xCPU:60 intervals,p95 16.8ms,0 intervals above33ms; not a physical-phone FPS guarantee. Optional native View Transitions/shared morphs and dark-theme UI remain explicitly deferred.


## Phase F — final verification, 2026-11-03

PASS — production browser suite ran against a fresh disposable database: **20/20 passed in 47.2s**. Backend regression:137 passed,1 skipped,1 existing Starlette/httpx deprecation warning. Build, lint and translation validation pass. Full responsive/text-zoom capture:375 cases, zero page-width overflows, zero undersized visible primary controls, one main and one primary heading per screen, no unexpected console errors. The final isolated Entry Lighthouse run scored 94 performance,100 accessibility,100 best practices. All documented numerical measurements are lab results.

The first full zoom capture found11 overflowing cases. After reproducing the constrained grid and flex behavior, minmax(0,1fr), min-width:0, control wrapping and long-word wrapping fixed the affected layouts. A capture run interrupted by rebuilding its asset directory was discarded and rerun on a stable production build. An earlier reused-database browser run failed on duplicate quiz titles; the authoritative final run starts a fresh fixture. A previous lazy-Copilot test race was fixed by awaiting the launcher, without weakening provider assertions. These unsuccessful checks are retained in this log rather than described as passing. The final test runner emits a harmless NO_COLOR/FORCE_COLOR warning; the backend deprecation remains unchanged.

## Summary

ClassPulse Atelier is implemented across the existing teacher and student journeys, with the AI Teacher Copilot integrated into the same visual system. Fluid Precision uses short, interruptible CSS/WAAPI motion, directional question/route entries, moving active indicators and immediate Lite/reduced-motion alternatives. English, Hindi and Telugu remain supported with498 matching keys each; all original 275 keys and values per language are preserved.

**Release decision: READY for local review and a prepared synthetic-data demonstration.** There are no known blocking functional regressions in the executed Chromium and backend checks. This is not a claim that every decorative example in the eight-part specification was implemented. Dark-mode UI, native View Transitions, shared-element morphs and spring physics are deferred. Existing backend generation also assigns activities; its explicit confirmation is preserved instead of inventing a draft-only endpoint. Inline live feedback is retained in place of a duplicate toast system.

Branch `main`; unchanged base HEAD `8fb7d628c6981b0cc3d2da548bb2ea40306825b0`. No new commit, push or deployment. Final verification date:2026-11-03. Existing uncommitted user work remains present. Comparison with the initial source checkpoint confirms no backend source, API-client contract, package.json or lockfile changes from this upgrade.

The existing database has the six genuine synthetic classes but no prepared diagnosis/group/assignment/reassessment loop. Prepare those through the real UI before presenting the full walkthrough. Live provider availability remains NOT TESTED; this does not block the verified mock-provider local workflow. See [three-minute-demo.md](three-minute-demo.md).

## Files Created and Modified

This inventory is relative to the **start-of-upgrade source checkpoint**, including the user's already-uncommitted quiz work. Git alone also shows earlier backend and package changes, which are not attributed to this upgrade. Machine-readable inventory: [change-inventory.json](upgrade-evidence/change-inventory.json).

### Created source and verification files

- `frontend/src/components/EffectsControl.jsx`
- `frontend/src/components/ui/Button.jsx`
- `frontend/src/components/ui/Card.jsx`
- `frontend/src/components/ui/Drawer.jsx`
- `frontend/src/components/ui/MobileDrawer.jsx`
- `frontend/src/components/ui/ProgressBar.jsx`
- `frontend/src/components/ui/QuestionPager.jsx`
- `frontend/src/components/ui/ScoreCard.jsx`
- `frontend/src/components/ui/StatusPill.jsx`
- `frontend/src/components/ui/Tabs.jsx`
- `frontend/src/context/EffectsProvider.jsx`
- `frontend/src/context/effectsContext.js`
- `frontend/src/hooks/useLiteEffects.js`
- `frontend/src/hooks/useModalDialog.js`
- `frontend/src/motion/ActiveIndicator.jsx`
- `frontend/src/motion/QuestionTransition.jsx`
- `frontend/src/motion/RouteTransition.jsx`
- `frontend/src/motion/presets.js`
- `frontend/src/styles/tokens.css`
- `frontend/tests/atelier.spec.js`
- `scripts/capture-upgrade.mjs`
- `scripts/measure-frontend-bundle.mjs`
- `scripts/profile-frontend.mjs`

### Modified source files

- `README.md`
- `frontend/index.html`
- `frontend/playwright.config.js`
- `frontend/public/favicon.svg`
- `frontend/src/App.css`
- `frontend/src/App.jsx`
- `frontend/src/components/AppShell.jsx`
- `frontend/src/components/LanguageSelector.jsx`
- `frontend/src/components/MetricCard.jsx`
- `frontend/src/components/PageHeader.jsx`
- `frontend/src/components/PageStates.jsx`
- `frontend/src/components/TeacherCopilot.css`
- `frontend/src/components/TeacherCopilot.jsx`
- `frontend/src/hooks/useAsyncData.js`
- `frontend/src/i18n/en.json`
- `frontend/src/i18n/hi.json`
- `frontend/src/i18n/te.json`
- `frontend/src/index.css`
- `frontend/src/pages/Assessment.jsx`
- `frontend/src/pages/ClassInsights.jsx`
- `frontend/src/pages/ClassProgress.jsx`
- `frontend/src/pages/Intervention.jsx`
- `frontend/src/pages/Login.jsx`
- `frontend/src/pages/Quizzes.css`
- `frontend/src/pages/StudentDashboard.jsx`
- `frontend/src/pages/StudentProgress.jsx`
- `frontend/src/pages/TeacherDashboard.jsx`
- `frontend/src/pages/TeacherQuizzes.jsx`
- `frontend/tests/quiz-workflow.spec.js`

Documentation/evidence: `docs/upgrade-progress.md`, `docs/three-minute-demo.md`, `docs/upgrade-evidence/skills.md`, `contrast.json`, `change-inventory.json`, `existing-backend-readonly.json`, baseline/final measurements, responsive PNGs, verification logs and `recordings/mobile-workflow-4x-cpu.webm`. Screenshot assets are review evidence and are not imported by the product. No files were removed. No PWA/service-worker files were changed because the active app had none. The existing `StudentQuizzes.jsx`, API services, role guard and session provider remain intact; shared quiz styling applies to both quiz roles.

Compatibility adapters: old global CSS aliases map to semantic Atelier tokens; original button/panel classes remain usable alongside the new primitives. `useAsyncData` retains its existing interface with additional refreshing state. No backend adapter or data migration was introduced.

## Dependencies Added with Sizes

**Runtime dependencies: none. Development dependencies: none. Removed dependencies: none. Additional dependency bytes:0.** Existing React19.3.1, React DOM19.3.1, Router7.18.5, Vite8.3.5, lucide-react1.66.0, Recharts3.10.1 and Playwright were reused. CSS and the native Web Animations API avoid an animation-package download. Cached CLI Lighthouse/formatting tools were used only for verification; package.json and package-lock.json are byte-identical to the checkpoint.

No local font assets were added; additional font transfer is0bytes. System Inter/Noto/system-ui fallbacks are used, with available Noto Devanagari and Telugu script coverage. No external font CDN or tracker was added. Exact raw, gzip(level9) and Brotli sizes are in [final/bundles.json](upgrade-evidence/final/bundles.json). Entry-route growth is reported below using the observed entry resource set, rather than summing every lazy route chunk.

## Design Tokens Summary

| Token group | Implemented values |
|---|---|
| Brand | #07584F; hover#06473F; active#043A34; tint#E8F5F1 |
| Surfaces | canvas#F8FAFC; main#FFFFFF; muted#F0F5F6 |
| Text | primary#162A3A; secondary#475569; on-brand#FFFFFF |
| Semantic | success#166534; warning#9A3412; danger#9F1239; information#1D4ED8; student amber#9A5B13/#FFF5E3 |
| Borders/focus | border#DCE6E8; strong control border#75888F; focus#07584F |
| Spacing | 0,4,8,12,16,20,24,32,40,48,64px |
| Radius | 6,10,12,16,20px; pill999px |
| Elevation | three low-opacity multi-layer shadows for surface, floating panel and dialog |
| Typography | 12,14,16,18,20,24,32px equivalents in rem; body1.5; headings1.35; Indic text1.6; tabular data numerals |
| Layout | max1440px; desktop sidebar248px, collapsed72px; topbar64px; compact sidebars220/200px at intermediate widths; modal navigation below 768px |

Light theme is implemented and tested. Dark semantic foundations exist in tokens.css but no supported dark-mode switch or full dark-page QA is delivered. Existing page-specific CSS is progressively mapped through compatibility aliases, so this is not a wholesale CSS architecture replacement.

Measured representative contrast: primary text/white14.72:1; secondary/white7.58:1; white/brand8.34:1; brand text/tint6.11:1; success/white7.13:1; warning/amber6.76:1; danger/pink7.25:1; strong control border/white3.70:1. [Contrast evidence](upgrade-evidence/contrast.json). Status text/icons accompany color.

## Motion System Summary

Central duration presets: instant0, fast120, status160, standard200, page260, modal280, drawer320, chart480, count600ms; toast220ms reference. Standard easing cubic-bezier(0.2,0,0,1), entrance(0.16,1,0.3,1), exit(0.4,0,1,1). CSS loading shimmer token1200ms; stagger references35ms, maximum 8 items / 650 ms. Spring presets are reference metadata only; no physics engine is shipped.

| Behavior | Actual implementation |
|---|---|
| Routes | Direction-aware WAAPI entrance with history index; single mounted tree; heading focus; best-effort history scroll map; immediate navigation, no exit wait |
| Questions | Shared Previous/Next pager, directional260ms entry, external answer state, focused heading, IME-safe intermediate Enter |
| Activity steps | Learn / Try / Finish tabs, selected indicator and shared question motion; backend controls completion and reassessment |
| Tabs/navigation | One decorative selected layer; transform interpolation and translated-label measurement; keyboard tabs remain semantic |
| Drawer/modal/Copilot | Standardized native top-layer dialogs and entrance tokens; Escape, Tab containment, opener focus, scroll cleanup; dismissal is immediate |
| Data | Exact final count text is stable for assistive technology; optional first integer count-up; bars retain true0–100 scale; Recharts animation disabled and numeric alternative supplied |
| Deferred | Native View Transitions, cross-page shared-element morphs, spring physics, completion ring and decorative list choreography |

Automatic Lite uses reduced motion, Save Data,2G/3G,<=4 GB device memory or<=4 logical cores. Missing capability APIs remain unknown, not a reason to block navigation. Manual Auto/Lite/Full persists in `classpulse-effects`; reduced-motion always takes priority over Full. Lite cancels route/question/indicator movement and smooth scrolling; original values and all tasks remain immediately usable. Storage denial is tolerated. No animation fabricates metrics, waits for pretend AI thinking, delays submissions or duplicates interactive route trees.

## Per-Page Status

COMPLETE below means the existing functional screen and its core Atelier presentation are delivered; optional choreography deviations are stated in the motion table.

| View | Status / actual implementation | Distinct improvement and verification |
|---|---|---|
| Entry | COMPLETE — `/login`, Login.jsx | Role-led learning-loop composition; browser entered both roles using real catalog and server student resolution |
| Teacher Dashboard | COMPLETE — `/teacher/overview` | Four prominent metrics and real next action/group previews; API-backed cards and all-language screenshots |
| Teacher Quizzes | COMPLETE — `/teacher/quizzes` | Shared Atelier controls and localized authoring; original publication/CSV/review/lesson tests pass |
| Class Insights | COMPLETE — `/teacher/insights` | Compact filtered records and evidence drawer; supporting quote, confidence and provider verified |
| Learning Groups | COMPLETE — `/teacher/interventions#groups` | Status filters/member dialog; review waits for real server response |
| Interventions | COMPLETE — `/teacher/interventions#assignments` | Explicit generate-and-assign confirmation and educator-review label; persisted assignments verified |
| Class Progress | COMPLETE — `/teacher/progress` | Honest zero-baseline score comparison/samples; failed refresh retains last data and retry passes |
| Student Dashboard | COMPLETE — `/student/dashboard` | Warm next-task emphasis; real student-scoped tasks and role checks pass |
| Student Quizzes | COMPLETE — `/student/quizzes`, `/:quizId` | Shared quiz presentation; existing reflection/repair/outage retry tests pass |
| Assessment | COMPLETE — `/student/assessment` | One question at a time; Next/Previous/language preserve answers and failed submit retries successfully |
| Assigned Activities | COMPLETE — `/student/interventions` | Clear actual assignment state; genuine activity opens in browser workflow |
| Intervention Activity | COMPLETE — `/student/interventions/:assignmentId` | Learn/Try/Finish structure; backend practice and completion verified |
| Reassessment | COMPLETE — embedded in StudentActivity | Directional questions and real result; submitted reassessment and persisted scores verified |
| Student Progress | COMPLETE — `/student/progress` | Samples and missing-data distinction; captured populated and empty states with API results |
| AI Teacher Copilot | COMPLETE — TeacherCopilot.jsx | On-demand modal and retained conversation; real existing API path, class context, IME and fallback labels tested with mock/stub providers |
| Unknown routes | COMPLETE — existing NotFound/RoleRoute | Return navigation and teacher/student role redirects verified |

## Test and Verification Matrix

Authoritative logs: [verification](upgrade-evidence/verification/). Browser tests use Chromium with the existing disposable mock-provider API and real SQLite persistence. Provider-specific presentation tests explicitly stub provider responses and are not live Gemini tests.

| Check | Result | Evidence / scope |
|---|---|---|
| Production build | PASS | `cd frontend && npm run build`, exit0, final-build.log |
| Frontend lint | PASS | `npm run lint`, exit0, no lint warnings |
| Translation parity/preservation | PASS | `npm run i18n:check`,498 keys each; original 275 values per locale preserved against checkpoint |
| Existing + added browser tests | PASS | `CLASSPULSE_TEST_PRODUCTION=1 npm run test:e2e`,20/20,47.2s; original4 remain |
| Backend regression | PASS | `cd backend && python3 -m pytest -q`,137 passed,1 skipped,1 pre-existing deprecation warning |
| Teacher and student entry | PASS | Browser catalog selection and student-code server resolution |
| Diagnosis evidence/group approval | PASS | Actual fixture diagnoses, members and server-confirmed review |
| Generate and assign | PASS | Confirmation required; real mock-provider API creates assignments |
| Assessment submission/recovery | PASS |503 preserves answers; retry persists submission |
| Practice/completion/reassessment | PASS | Genuine server grading/completion and stored result |
| Copilot send/context/reopen | PASS | API conversation, same-class context, close/reopen state, language/IME; provider labels tested separately |
| Keyboard navigation | PASS | Automated keyboard interactions for Tab edges, Escape, question controls, tabs and route headings; no complete manual AT audit implied |
| Modal focus/scroll cleanup | PASS | Dialog boundary cycling and opener focus assertions; background inert via showModal |
| Reduced/manual Lite | PASS | Preference persistence; reduced overrides Full; class/form state retained |
| Auto Lite | PASS | SaveData,3G,4GB,4cores,unknown APIs separately tested |
| Back/Forward | PASS | Correct URL and primary focus, single active main/heading |
| Nested refresh/deep links | PASS | Page reload, direct nested page entry, group/assignment hashes and role redirect tests |
|360/414/768/1024/1440px | PASS |375 capture cases; all languages, populated views,200%root text; zero page overflow |
| English/Hindi/Telugu | PASS | Full layout matrix + language switches preserve forms/Copilot/class |
| Touch targets | PASS | No visible principal controls below44px in captured views; student main actions 48px |
| Unexpected console errors | PASS | console-errors.json empty; intentional503 fault tests excluded from normal-flow error claims |
| Entry performance/CLS | PASS | Latest Lighthouse94/100/100,CLS0.0002724; entry growth below 40 KiB |
| Original API contracts | PASS | API-client source and backend byte-identical to checkpoint; original backend/browser tests pass |
| Existing database smoke | PASS | Nov3 read-only GET checks at 8011; six actual catalog classes |
| Service worker/install/offline shell | NOT TESTED | No baseline manifest, worker or registration exists; not installable; no offline submission guarantee |
| Interactive screen-reader speech | NOT TESTED | No Orca/NVDA speech session performed; binary availability alone is not testing |
| Physical Android/iOS and Safari/Firefox | NOT TESTED | Chromium desktop emulation only |
| Live Gemini/OpenRouter | NOT TESTED | Key presence/configuration checked without printing it; no paid/live request issued |
| Field INP / physical-device FPS | NOT TESTED | Only lab frame intervals and long tasks measured |

Reproduce checks from the repository root:

```bash
cd frontend
npm run build
npm run lint
npm run i18n:check
CLASSPULSE_TEST_PRODUCTION=1 npm run test:e2e
cd ../backend
python3 -m pytest -q
```

The browser configuration starts/stops its own temporary API on 8012 and preview on 5181. Those ports must be free; it never resets the existing database on 8011.

## Performance Numbers Before vs After

| Measurement | Before | After | Difference / interpretation |
|---|---:|---:|---|
| Entry JS raw resource bytes | 431771 | 455048 | +23,277 bytes |
| Entry JS gzip bytes | 132901 | 140405 | +7,504 bytes = 7.33 KiB; below 40 KiB gate |
| Entry JS Brotli bytes | 115359 | 118549 | +3,190 bytes |
| Observed JS transfer bytes | 134770 | 144931 | +10,161 bytes; includes transfer overhead |
| Entry stylesheet gzip bytes | 9225 | 11124 | +1,899 bytes |
| All CSS assets gzip bytes | 11242 | 17846 | +6,604 bytes; includes lazy CSS |
| Additional fonts transferred | 0 | 0 | No added font request |
| Entry Lighthouse performance | 98.0 | 94.0 | Target >=90 passes; final score lower |
| Entry Lighthouse accessibility | 95.0 | 100 | Target >=95 passes |
| Entry Lighthouse best practices | 100 | 100 | Unchanged |
| Lighthouse LCP ms | 2302.1 | 2396.91 | +94.81 ms |
| Lighthouse CLS | 0 | 0.0002724005299041049 | Both below 0.05 |
| Slow3G +4xCPU LCP ms | 4340 | 5084 | +744 ms; single-run lab sample |
| Slow3G +4xCPU CLS | 0 | 0 | No observed entry layout shift |
| Slow3G +4xCPU long tasks ms | [82] | [139, 73] | No field INP claim |

Method: Chromium headless; entry route resource set; gzip level9 and native Brotli per actual file. Transfer size includes server encoding/headers and is reported separately. Baseline and current assets were measured with the same script; Vite's displayed gzip uses its own compressor settings. Lazy route chunks are not charged as entry. Scripts: `scripts/measure-frontend-bundle.mjs`, `scripts/profile-frontend.mjs`. Exact details are in baseline/final JSON files.

The entry is modestly larger and slower on the strict Slow3G sample; this upgrade does **not** claim it made first load faster. The40KiB entry growth, Lighthouse>=90 and CLS<0.05 gates pass. Deferred shell/Copilot splitting contains entry growth; Recharts stays lazy, fonts add0bytes, no motion library is shipped. CPU/network numbers are single-run lab observations, not field guarantees. Lighthouse also scored 98 in an earlier run and 93 during concurrent browser tests; the final isolated result 94 is the reported final measurement, not a selected best score.

4xCPU question-transition frame sample:60 intervals, 95th percentile16.8ms,0 above 33 ms. [Motion sample](upgrade-evidence/final/motion-performance.json). A short prerecorded [mobile workflow](upgrade-evidence/recordings/mobile-workflow-4x-cpu.webm) is explicitly an engineering recording. It does not prove steady60FPS on a low-end phone.

## Accessibility Results

Automated tools: Lighthouse/axe-core Chromium entry audit100, Playwright role/focus/keyboard assertions, computed control geometry and viewport overflow checks, plus programmatic sRGB contrast calculation. Representative final PNGs were visually inspected, including teacher/entry/mobile/multilingual views. Contrast ratios above apply to tested pairs; a100 automated score does not establish full WCAG conformance.

Keyboard-driven browser checks exercised focus after navigation, drawer open/Tab/Escape/return, questions, language controls, error retry and native form interaction. There was no full manual screen-reader speech session. Live regions retain real pending/error information; the final counter value has a stable assistive label. Chart values remain available in text. Native modal dialogs make the workspace inert and preserve focus on close. Reduced motion turns off optional movement even after Full was selected.

All five widths in English/Hindi/Telugu and 200%root font size were checked for overflow. This is text-size stress testing, not a claim of testing every browser zoom mode. Status text accompanies color, labels are not uppercased/tracked in Indic scripts, and language changes update html lang without remounting input state. No known blocking accessibility issue remains in the exercised paths. Screen-reader speech, browser/OS differences and400%reflow remain follow-up validation, so no comprehensive WCAG certification is asserted.

## Known Limitations

| Severity | Limitation and recommended follow-up |
|---|---|
| Medium | Live Gemini/OpenRouter requests NOT TESTED. Run a clearly labeled synthetic-class request before an event and inspect returned provider/fallback status. |
| Medium | Existing database lacks a prepared full loop. Use real UI operations or isolated mock harness to prepare diagnosis, approved group, assignment and reassessment before the timed demo. Guide is ready; dataset is not pre-filled by this upgrade. |
| Medium | No interactive screen-reader speech or physical-device/Safari/Firefox check. Validate these before a wider production release. Automated accessibility evidence is narrower. |
| Medium | Backend has no separate intervention draft approval endpoint; existing operation generates and assigns to approved groups. UI explicitly confirms it; separate editorial draft lifecycle needs future backend work. |
| Low | Full dark-mode UI, native View Transitions, cross-route morphs and physics springs deferred. Light theme and optional CSS/WAAPI entries are supported. |
| Low | Diagnosis endpoint contains supporting quote, not full original response. Drawer discloses this limit. Add a scoped backend response field only in a future API task. |
| Low | No baseline PWA/install/offline implementation. Network failure is recoverable online; offline submission is unsupported. |
| Low | System-script font availability differs by device; no fonts are bundled. Validate target devices and self-host licensed subsets only if necessary. |
| Low | Historical scroll is best-effort and route tests assert URL/focus, not exact scroll pixels. Nested server deployments still require SPA history fallback, as before. |
| Low | Long existing CSS retains compatibility aliases; native dialogs and WAAPI depend on modern browser support. Review actual school browser versions before rollout. |
| Low | Backend regression emits existing Starlette/httpx deprecation; resolve as a separate dependency change. One pre-existing test is skipped. |

No authentication/privacy semantics were changed. Demo-role access is visibly identified and is not production authentication. No private API caching or service-worker cache was introduced. No secrets or local databases are staged. These limits allow local demonstration; they do not constitute production-authentication or educational-effectiveness certification.

## Honesty Statement

Classroom metrics come from backend records; animation does not invent activity, scores or learning gains. The test harness uses labeled synthetic data and mock/template generation in an isolated temporary database. Provider-specific intercepted fixtures exist only in tests. Actual educational drafts still require teacher review. Before/after samples and question differences do not prove that an intervention caused improvement.

Live Gemini/OpenRouter interactions were **NOT TESTED**. Screen-reader speech and physical-device performance were **NOT TESTED**. Missing measurements are not described as passing. No new student records were fabricated in the existing database for screenshots or presentation. Screenshot/recording records were prepared through genuine API workflows in the disposable fixture. Existing user source changes were preserved; no backend business rules, student headers or API contracts were rewritten for the visual upgrade.

## Pre-merge self-review checklist

YES/NO below follows Section21E. “YES” refers to the stated implementation and exercised scope; it is not a substitute for the limitations above. Every NO includes severity and evidence. No critical or high functional NO remains.

| # | Check | Answer | Evidence / limitation |
|---:|---|---|---|
| 01 | Does the application build successfully? | YES | Production build exit0. |
| 02 | Does the frontend lint pass? | YES | Lint exit0. |
| 03 | Do the existing frontend tests pass? | YES | All4 original tests plus16 new tests pass. |
| 04 | Do relevant backend regression tests pass? | YES | 137 passed;1 pre-existing skip. |
| 05 | Are existing API contracts preserved? | YES | Backend and API clients unchanged from checkpoint. |
| 06 | Are all original routes accessible? | YES | Route inventory, role/deep-link tests and page captures. |
| 07 | Is Teacher entry functional? | YES | Real catalog teacher-entry browser test. |
| 08 | Is Student entry functional? | YES | Server-resolved student-entry browser test. |
| 09 | Does subject selection use actual available subjects? | YES | Subjects derive from live demo catalog. |
| 10 | Does class selection use actual backend records? | YES | Six existing backend classes; read-only smoke passes. |
| 11 | Does the Teacher Dashboard show real statistics? | YES | Summary cards consume existing backend responses. |
| 12 | Are AI diagnosis uncertainty labels preserved? | YES | Confidence, provisional/follow-up and provider labels retained. |
| 13 | Can teachers inspect diagnosis evidence? | YES | Evidence dialog browser assertion; exact quote and API limit visible. |
| 14 | Can teachers review learning groups? | YES | Member dialog and group review workflow passes. |
| 15 | Do approvals wait for backend confirmation? | YES | Existing server response controls success; browser review/assignment passes. |
| 16 | Are intervention drafts visibly identified? | YES | Copilot/quiz drafts labeled; intervention educator-review warning discloses atomic assignment limitation. |
| 17 | Are real provider and fallback states distinguishable? | YES | Original Gemini/template label test passes; no live provider claim. |
| 18 | Can students complete existing assessments? | YES | 503/retry then successful server submission. |
| 19 | Are student answers preserved across question transitions? | YES | Previous/Next assertions preserve stored answer. |
| 20 | Are student answers preserved after network errors? | YES | Injected503 leaves answer and successful retry works. |
| 21 | Can students complete intervention activities? | YES | Real practice and completion browser workflow. |
| 22 | Can students complete reassessments? | YES | Real reassessment submission and persisted score verified. |
| 23 | Are progress values taken from backend records? | YES | Progress API retained; original backend regression passes. |
| 24 | Are progress sample sizes visible? | YES | ScoreCard samples visible in final progress captures. |
| 25 | Is non-causal progress framing retained? | YES | Non-causal comparison note retained. |
| 26 | Does the AI Teacher Copilot preserve class context? | YES | Context-key guard preserved; send/reopen/language tests pass. |
| 27 | Does AI Copilot use the existing backend API? | YES | Existing /copilot/chat and context APIs unchanged. |
| 28 | Is the OpenRouter API key absent from frontend bundles? | YES | Built assets scanned; no key patterns. No key is serialized by UI. |
| 29 | Are there no hardcoded fake AI responses? | YES | No production AI fixture; mocks/intercepts confined to test harness. |
| 30 | Are route transitions direction-aware where implemented? | YES | Central direction helper uses pathname depth and history index. |
| 31 | Does browser Back restore the correct route? | YES | goBack route/focus assertions pass. |
| 32 | Does browser Forward restore the correct route? | YES | goForward route/single-main assertions pass. |
| 33 | Is keyboard focus restored after navigation? | YES | Primary heading focus assertions pass; language does not steal it. |
| 34 | Do modal drawers trap and restore focus correctly? | YES | Native dialog + explicit Tab edge trap; opener focus assertion. |
| 35 | Does Escape dismiss the appropriate overlays? | YES | Mobile/evidence/Copilot Escape checks pass. |
| 36 | Are primary controls at least 44px in effective touch size? | YES | 375-case target scan reports no undersized principal controls. |
| 37 | Does reduced motion disable nonessential movement? | YES | Reduced preference overrides Full and cancels optional motion. |
| 38 | Does Lite effects mode operate correctly? | YES | Manual Lite browser test passes. |
| 39 | Is the Lite effects preference persisted? | YES | Reload retains classpulse-effects selection. |
| 40 | Does the English interface render correctly? | YES | English screenshots/layout matrix. |
| 41 | Does the Hindi interface render correctly? | YES | Hindi screenshots/layout matrix. |
| 42 | Does the Telugu interface render correctly? | YES | Telugu screenshots/layout matrix. |
| 43 | Does language switching preserve forms and class context? | YES | Question/Copilot input and topbar class retained in tests. |
| 44 | Are there no clipped translations at 360px? | YES | 360px all-language full page/text-zoom matrix passes. |
| 45 | Is the 414px layout usable? | YES | 414px matrix passes. |
| 46 | Is the 768px layout usable? | YES | 768px matrix passes. |
| 47 | Is the 1024px layout usable? | YES | 1024px matrix passes. |
| 48 | Is the 1440px layout visually balanced? | YES | 1440px captures visually reviewed; max-width layout. |
| 49 | Are important text contrast requirements satisfied? | YES | Representative essential text pairs6.11:1–14.72:1; entry axe audit100. |
| 50 | Are chart values available without relying on animation? | YES | Numeric chart alternative, samples and text survive Lite. |
| 51 | Do count-up animations finish at exact backend values? | YES | Final DOM uses exact backend value; counter cleanup restores same formatted value. |
| 52 | Are missing statistics distinguished from zero values? | YES | Null displayed as Not available; numeric0 retained. |
| 53 | Do loading indicators represent actual pending operations? | YES | Only actual pending state renders progress indicators. |
| 54 | Are artificial AI-thinking delays absent? | YES | No artificial AI wait; API pending drives feedback. |
| 55 | Are user interactions responsive during transitions? | YES | Single mounted route and immediate controls; rapid history test passes. |
| 56 | Are large animations disabled or reduced on constrained devices? | YES | SaveData/3G/memory/core branches select Lite. |
| 57 | Is entry-route JavaScript growth within 40KB gzip? | YES | +7.33 KiB gzip vs40KiB budget. |
| 58 | Is cumulative layout shift below the stated target where measured? | YES | Latest entry Lighthouse CLS0.0002724; Slow3G0 (<0.05). |
| 59 | Are locally bundled font files properly licensed and optimized? | YES | No bundled font files, so licensing/optimization adds no new requirement. |
| 60 | Are third-party trackers and external font CDNs absent? | YES | Source/network inspection; system fonts only. |
| 61 | Does the existing PWA installation behavior remain functional? | NO | Low severity — baseline has no manifest/service worker/install behavior. No existing PWA can be verified; separate implementation needed if requested. |
| 62 | Are private classroom API responses protected from unsafe caching? | YES | No private API cache/service worker added; existing client behavior preserved. |
| 63 | Are error states recoverable? | YES | Assessment/Copilot/quiz outage and progress refresh retries pass. |
| 64 | Are empty states useful and truthful? | YES | Backend-driven missing-data/empty states captured; no invented records. |
| 65 | Are there no unexpected browser console errors? | YES | Normal-flow console-errors.json empty; intentional503 cases separately labeled. |
| 66 | Are screenshots captured for representative responsive views? | YES | Initial27 plus all-page final multilingual/responsive PNGs. |
| 67 | Are available performance measurements recorded? | YES | Before/after JSON, Lighthouse and4xCPU/Slow3G profiling recorded. |
| 68 | Are unavailable tests marked NOT TESTED? | YES | Live provider, screen-reader speech, physical hardware and field INP explicitly NOT TESTED. |
| 69 | Is docs/upgrade-progress.md complete? | YES | Audit, phases, exact final report headings, evidence and checklist included. |
| 70 | Is docs/three-minute-demo.md ready for presentation? | YES | 175-second guide and truthful preparation/fallback/run commands ready; data/provider preflight remains required. |

## Run and demonstrate

From `openpost/backend/`:

```bash
python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8011
```

From `openpost/frontend/`:

```bash
CLASS_PULSE_BACKEND_URL=http://127.0.0.1:8011 npm run dev -- --host 127.0.0.1 --port 5173
```

Open `http://127.0.0.1:5173/login`. Reuse those processes if already running. For production local preview, `npm run build`, then `CLASS_PULSE_BACKEND_URL=http://127.0.0.1:8011 npm run preview -- --host 127.0.0.1 --port 5179`. Port8000 belongs to another service in this workspace. No database migration/reset is needed for these frontend changes.

Recommended demonstration: Entry→Teacher summary→Class Insights/evidence→reviewed group/intervention→Copilot→Student activity/question→Progress samples→Telugu→Lite. Follow the 175-second timeline and truthful preparation/fallback steps in [three-minute-demo.md](three-minute-demo.md). Nothing has been pushed or deployed.
