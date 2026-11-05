# Source-derived API inventory

Credential mode applies a global session/CSRF/role/class dependency.
Local demo mode is explicitly self-asserted. This inventory describes definitions;
runtime evidence is in [FINAL_IMPLEMENTATION_REPORT.md](FINAL_IMPLEMENTATION_REPORT.md).

| Method | Path | Request / response schema | Access |
|---|---|---|---|
| GET | `/api/classes/{class_id}/misconception-map` | MapSummary | Authorized class teacher; latest-attempt summary, no response bodies |
| GET | `/api/classes/{class_id}/misconception-map/evidence` | EvidencePage | Authorized class teacher; code/student/review/uncertainty filters; limit 1–100 (default 20), offset ≥0 |
| GET | `/api/students/{student_id}/journey` | JourneyPage | Own student or authorized class teacher; limit 1–100 (default 30), offset ≥0 |
| GET | `/api/system-status` | Safe status JSON | Current account/role; local app/database/configuration, no provider request |

These four additions preserve existing response contracts. Existing correction
POST and group review PATCH remain authoritative. Group approval rejects foreign
members or proposals with fewer than two members; support generation rechecks
foreign members even on legacy approved proposals. No schema migration is added.
The pre-existing source-inventory exporter produced an empty route table in this
environment; the entries above were verified against FastAPI's OpenAPI paths.

Map period fields describe response timestamps; queried_at is query time, not live
inference time. Null periods mean no eligible source responses. Summary total
includes pending latest responses; concept counts include CORRECT/FOLLOW_UP and
sum to total minus pending diagnoses. Each detail item identifies original student
text, AI explanation and saved correction separately. Student journey omits private
teacher correction reasons. Required-auth mode derives role/class access from the
session; self-asserted local demo mode remains compatible and is not authentication.
