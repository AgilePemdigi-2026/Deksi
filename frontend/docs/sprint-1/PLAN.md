# Batch 2 — frontend Sprint 1, full Prototype 2 port

## Outcome and ownership

Sole implementer in `integration/sprint-1-dashboard-fe`, new worktree based on FE7 `94a05cd1fe5044d3d7e0f71ad6d0487edd5f921f`. Do not modify original FE/auth/backend worktrees, design prototypes, agent configuration or existing checkpoints. No installation, commit, push, PR, Git merge or provider calls. Backend public dependency is the uncommitted, verified Batch 1 candidate, read-only.

Visual authority: `E:/Deksi-Design-Prototypes/prototype-2/index.html`, selected SHA-256 `1bedb30ee30c3c180bf947083259d063f257a8cf518935eec2829dd2d06e5503`. Authoring reference: `E:/Deksi-Design-Prototypes/references/prototype-2/dashboard/`. Prototype demo numbers/narratives are not economic API data.

## Item 1 — protected consolidation

- Preserve original FE6/FE7 dirty bytes with source snapshots, HEAD/status and hashes before porting; compare originals after completion. Snapshot: `C:/Users/Pongo/AppData/Local/hermes/cache/scratch/deksi-b2-snapshot-t4jkxhbb/preservation.json`.
- Port the seven shared precision/provenance/calendar repair source/test files from FE7 after confirming the matching FE6 overlay; preserve old receipts as historical evidence.
- Reuse Login and Reset from Reset FE `2c441e54ccc0a45f1617e11e547e7b260353f7ce`, including existing clients, assets and tests; merge routes semantically, not by replacing App wholesale.
- Adapt Filter/Feedback from team commit `f638bf8d5c40f91076caa893dac44d62a2049b88`, not backend or Sprint 2 source-data pages. Feedback must bootstrap a same-origin CSRF token/cookie and POST with the token; no exemptions.
- Use existing installed dependencies only, with build/cache/artifacts under the new worktree. Public data and authentication APIs have distinct readiness; do not fabricate successful authentication if the public backend does not provide it.

## Item 2 — full dashboard port and verification

- Port the full selected composition, real supplied images/fonts and substantive dashboard interactions, not only old card CSS. Keep all eight Sprint 1 features: Admin Login, Reset, Summary, Trend, Filter, Detail, Source Trace, Feedback.
- Preserve missing/zero/exact decimal distinctions, units and native periods; map prototype aliases `apbn`/`bi-rate` to API `fiskal`/`birate`, without copying incompatible labels or calculations.
- Filter selected-year summary and displayed native history consistently; do not recompute core economic metrics or represent the backend global average as a filtered-range average. Keep source selectors/guard tied to the selected observation and refuse mixed series or missing calendar bridges.
- Show real loading/empty/error/retry states. No demo data fallback, unverified AI narratives or Sprint 2 catalog routes for navigation completeness.
- Tests: new pure adapter/CSRF/route assertions RED before behavioral changes; preserve/re-run relevant existing feature/auth suites; build and scoped lint, actual browser against the unchanged public backend using fresh isolated scratch DB/RAW and free loopback ports. Test provider/network routes are prohibited.
- Keep user/browser profiles untouched. All logs, media, DB and fixture writes belong to the new frontend/scratch, never the backend dependency. Runtime settings must not read user .env or DB; disable bytecode writes into dependencies.
- Deliver rendered preview/captures and technical results separately from aesthetic approval. Do not repeat the unchanged 97-test backend suite or modify canonical agent recipes to obtain a badge.

## Stop conditions and remaining gates

Report before changing any backend/API. No installation or publication without new permission. If auth consolidation is unavailable, retain real frontend routes and honest failure states, report that acceptance boundary, and continue independent public-dashboard work. Human visual approval remains pending until actually received. Preserve prototype/source snapshots and compare protected hashes before final handoff.
