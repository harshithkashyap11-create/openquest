# Current map/journey limitations — 2026-11-05

- Independent educator evaluation is **NOT TESTED**: no approved educator labels
  or held-out source records exist. `evaluation-status.json` has zero examples and
  null metrics. Synthetic regression tests validate software accounting only.
- English/Hindi/Telugu interface strings have not received independent educator
  review. Source question text, original answers and stored model text retain
  their original language. Confidence is not calibrated.
- The map includes latest attempts per question; historical attempts remain in
  the student story. Existing Class Insights and grouping retain their historical
  selection rules. Groups select a primary suggestion by confidence and may not
  match every latest map pattern; inspect the persisted membership before approval.
- Reviewed means a correction record exists. Legacy status-only suggestions are
  still awaiting review on the map; the map does not invent a reviewer from a
  teacher_reviewed status or synthetic fixture label.
- Source responses have no explicit assignment foreign key. The story shows
  chronological response history and actual assignment/reassessment links; it
  cannot attribute an intervention to one specific answer or demonstrate causality.
- The fresh demo safely starts over in a new directory. A destructive synthetic
  reset is **DEFERRED**: a database marker cannot prove no real records were added.
  Previous rehearsal databases are retained, never deleted automatically.
- Feedback persistence/aggregation, roster import, curriculum provenance,
  cross-subject profiles and school aggregates remain deferred. Current student
  identity is class-bound; no school administrator boundary exists.
- Demo identity is self-asserted and local only. Required-auth mode enforces
  server identity and ownership; no account recovery, retention/deletion workflow,
  hosting or backups were added. No production-readiness claim is made.
- Offline support remains downloaded material and queued practice; new inference,
  teacher decisions and reassessment require connectivity. Browser storage is
  unencrypted, may be evicted, and conflicts require teacher review. No background
  synchronization or fully offline claim is supported.
- System status distinguishes configuration from reachability. Provider inference
  is not probed by the status page. Live provider smoke and PostgreSQL execution
  remain **NOT TESTED** in this work.
- Human screen-reader testing, independent language review, real-device slow-network
  testing and a timed three-minute human rehearsal remain **NOT TESTED**.

The earlier upgrade's detailed limitations are retained below for context.

# Known limitations and unresolved acceptance work

The upgrade does not implement every requirement in the eight-part specification.
Do not infer production or educational validation from passing software checks.

| Limitation | Impact / mitigation |
|---|---|
| Independent diagnosis evaluation and language adjudication absent | Real-world accuracy, calibration and language quality remain NOT TESTED. Use human references and the supplied evaluation methodology. |
| No causal learning study | A changed reassessment result demonstrates stored evidence, not educational impact caused by the app. |
| Tutoring quality is not independently evaluated | Default misconception ladders and opt-in live response-aware hints work through bounded APIs. Feedback is provisional; fully adaptive question selection remains incomplete. Difficulty is a recommendation. |
| One subject/topic class and one class per student | Demo uses separate Mathematics/Science/English contexts; unified cross-subject school membership is future schema work. |
| Grouping uses one primary misconception | Learner ledger can retain several gaps, but overlapping instructional groups are not fully implemented. |
| Regional authored templates limited to M01 | Live regional lesson drafts can be requested; other regional fallback/tutor requests fail explicitly. Broad multi-subject language quality is unverified. |
| No canonical-source translation workflow | Independently generated drafts are not synchronized translations; source revision invalidation for translations is not implemented. |
| Manual teacher answer/language attestation | Structural validation and sampled arithmetic checks do not independently prove arbitrary generated question keys correct. Teacher review remains necessary. |
| No per-section regeneration or rich lesson editing | Existing structured fields can be revised; editor does not expose every optional pedagogical field. Save before reload. |
| Unsaved draft edits may be lost on reload | Saved revisions persist; save before changing workspace. |
| Offline scope is downloaded lessons and assigned practice | New inference, protected reassessment, teacher approvals and new hint generation require connectivity. No offline Gemini. |
| Browser storage is not encrypted or guaranteed durable | Shared phones and browser eviction need operational safeguards. Pending conflicts can block logout until reviewed; export/conflict-resolution UI is incomplete. |
| Offline retries are foreground-driven | No mobile background sync guarantee. Open Learning Lab and synchronize after reconnecting. |
| No historical live-database evidence backfill | New events and the isolated demo are connected; old imported diagnoses are not silently rewritten into the new ledger. |
| No durable background diagnosis jobs | Saved submissions can retry; reconciliation after process crashes is not a scheduled worker. |
| Per-class evidence queries are not optimized for school scale | N+1 reads/history payloads remain; verify load and add pagination/projections before large deployment. |
| Production controls remain | HTTPS/reverse proxy, CSP, distributed rate limits, retention, account recovery, backups and independent security review are required. Local demo identity is deliberately not authentication. |
| PostgreSQL new migration and real Android performance unverified | SQLite/browser emulation evidence must not be extrapolated to those environments. |
| Optional voice, guardian summaries and printable packs absent | P2 features are deferred to preserve the core loop. |
| Three-minute timed human rehearsal not verified | Automated cycle and lesson/offline browser tests do not guarantee a live presentation fits the timetable. |

Current external dependencies: configured provider credentials, network and quota;
local SQLAlchemy database and browser storage. See [FINAL_IMPLEMENTATION_REPORT.md](FINAL_IMPLEMENTATION_REPORT.md)
for measured results and the final verdict. No paid service or provider was silently
substituted and no commit/push was issued by this agent.
