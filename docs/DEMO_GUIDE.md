# Reproducible three-minute demonstration

Use INSTALLATION.md to initialize and start the dedicated demo. Select Mathematics
→ Fractions → Synthetic ClassPulse · Mathematics. Its CP-M01-01 and CP-M01-02
records are explicitly **hand-authored synthetic fixtures**, model
synthetic-fixture-v1 / provider mock. Science and English have separate contexts
because the existing schema scopes one subject/topic per class.

Keep a teacher tab and a student tab ready in separate browser profiles/contexts.
Use local demo mode only on loopback, or sign in with the generated local accounts.
For live inference, start the demo API with the existing configured provider and
run the bounded provider smoke check first. Do not reset the original database.

| Time | Navigation and spoken explanation |
|---|---|
| 00:00–00:20 | Teacher Overview then Learning evidence. Say: “ClassPulse AI identifies why students struggle, not just whether their answers are wrong.” Identify the saved M01 evidence and synthetic fixture provenance. |
| 00:20–00:45 | Student Assessment: submit “2/5” and reasoning “I added the numerators and denominators.” Teacher Overview: run diagnosis. Show evidence, provider/model and uncertainty in Class insights. If more baseline questions are present, prepare all responses before the timed run. |
| 00:45–01:05 | Teacher Learning evidence: show the new event, heuristic category, evidence count and bounded recommendation. Learning groups: generate a proposal. |
| 01:05–01:30 | Review the M01 group and approve its exact membership; generate the intervention. Open Adaptive Lesson Studio (or the M01 link in Learning evidence), choose Telugu, generate or reopen a labeled draft. Show objectives, correction and worked example. Review keys/language, approve, publish, and attach to matching approved activities. |
| 01:30–02:05 | Student Learning Lab: open the approved activity and request hint one, describe a step, request hint two. Switch UI language to Telugu for the M01 ladder. Show the template provenance, or explicitly select live AI for response-aware guidance. Both remain provisional and do not add independent mastery credit. |
| 02:05–02:35 | Submit the three practice responses, return to Interventions, complete the activity, then submit the independent reassessment. Show progress and the updated evidence history. M01 practice keys: 5/12, 1/2, 7/8. Reassessment keys: 11/12, 7/10, 13/24. These are preparation notes, not keys exposed to the student API. |
| 02:35–03:00 | Download the published lesson while online, disconnect, reload Learning Lab, and show the previously downloaded content. Say that new AI inference requires a connection. Finish on teacher control, multilingual access and traceable evidence. |

Real inference latency varies and lesson generation can exceed the allotted 25
seconds. Prepare an approved draft before the timed run and clearly identify it as
previously generated. Do not call that draft fresh live inference. A complete timed
three-minute human rehearsal has NOT been established; the deterministic API cycle,
production UI lesson publication and offline reload have automated evidence.

If inference is unavailable, show that the assessment is saved and retry later.
An explicitly requested labeled template can support lesson generation. Never
present template/rule output as Gemini. Mock diagnosis for Science/English abstains;
show live subject smoke evidence separately or switch to the synthetic teacher-
reviewed fixtures with an explicit disclosure.

Recovery:

- Browser reload: saved attempts, decisions, hint history, lesson revisions and
  published links come from the database. Unsaved editor keystrokes may need to be
  entered again; click Save new revision before switching workspaces.
- Retry a lesson command with unchanged settings: the frontend reuses its pending
  request identity. A changed command receives a new identity.
- Retry a reassessment: identical saved answers return the prior result. Different
  answers conflict and cannot replace a completed score.
- Offline practice: download the activity, save responses in Learning Lab, reconnect
  and synchronize. Pending/conflicting responses stay on the device; server scores
  are authoritative. Logout refuses to silently discard unsynchronized work.
- Restart: stop only the demo process, restart using the same marked demo file,
  reload the browser. Seeding again preserves records and does not duplicate them.

Troubleshooting: /health is liveness, /health/ready checks DB access, /health/ai is
configuration only. Missing keys or provider 429/503 are separate from DB failure.
Use Vite's configured same-origin proxy; do not add permissive CORS as an emergency
fix. If migrations are missing, inspect the chosen DB and run the documented
additive migration; do not delete data. No emergency manual SQL edits are required.
