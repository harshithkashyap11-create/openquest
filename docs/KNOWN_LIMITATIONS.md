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
local SQLAlchemy database and browser storage. See FINAL_IMPLEMENTATION_REPORT.md
for measured results and the final verdict. No paid service or provider was silently
substituted and no commit/push was issued by this agent.
