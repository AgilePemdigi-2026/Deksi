# Backend F6/F7 — implementation and integration plan

Date: 2026-11-03. User authorized completing scoped backend work, evaluation/repairs and preparing feature branches for a later push. No push, PR, merge, Git identity change or external provider acquisition.

## Goal and inspected baseline
- Deliver compatible public Django APIs consumed by the existing published React FE, exercise them through the actual browser, and leave separate F6/F7 local feature checkpoints ready for publication.
- Repository: AgilePemdigi-2026/Deksi; base origin/main 0e92899ce54f85440fe920ca457dfd91f747e1aa. Active FE backend subtree equals this base. origin/be c5c1155 is a different scaffold and is NOT the implementation base.
- FE F6 13a7680e96c1170cb9dcc041577e626760d8d76f and F7 94a05cd1fe5044d3d7e0f71ad6d0487edd5f921f remain unchanged. Login and cancelled historical backend branches remain untouched.
- Existing models: Indicator, Observation, Source, RawFile, DataUpdateLog. Existing consumers use summary, trend, source-trace and local RAW download routes. No new read framework/router/provider dependency is needed.
- Legacy storage has mutable observations and source masters, no formula/input ledger or immutable revision journal. This delivery must expose that limitation honestly; no invented historical version, approval, formula/input, official verification or AI narrative. Historical source acquisition is not a runtime fallback.

## Batch 1 — F6
### 1. Isolated base and executable test infrastructure
- New worktree feature-6-detail-be / feat/6-detail-indikator-be from the pinned main.
- Add minimal backend requirements entrypoint reflecting actual runtime imports; reuse the existing compatible interpreter read-only (Login venv, Django 6.1.2) without installing/changing its packages.
- Add explicit Django test settings independent of user .env and databases. Synthetic records and RAW files must stay in owned scratch directories. No database backup restoration or ingestion.
- Establish baseline HTTP behavior, then RED/GREEN regression tests with saved command logs.
### 2. Public detail correctness
- Keep established JSON route/field compatibility; reuse models and deterministic Decimal arithmetic.
- Public published data requires actual recorded review; never include pending/validated/rejected records or private validation/reviewer details.
- Select comparable previous rows and sparkline by source/unit/frequency/data type. Clearly distinguish percent from percentage-point differences; zero denominators stay unavailable.
- Preserve native frequency and exact source values; reject incompatible aggregations rather than combining unlike observations. Do not invent calendar availability or official interpretations.
- Test unknown/empty/public access, method restrictions, ordering, precision, mixed semantics and dashboard compatibility.

## Batch 2 — F7
### 3. Source Trace consistency
- New feature-7-source-trace-be / feat/7-source-trace-be stacked on verified F6 checkpoint.
- Preserve value, period, unit, source and RAW relationship for each observation. Do not erase RAW metadata merely because two observations share its checksum.
- Validate exact selection/pagination if added; reject missing/ambiguous context without newest fallback.
- Provide public metadata allowlist and safe HTTP(S) links only, explicit unavailable formula/version/verification fields. No network calls to source links.
### 4. RAW safety and preservation
- Require reviewed public indicator/source/RAW relationship; constrain reads to configured RAW root, reject traversal/symlinks/missing/non-file/oversized content, validate SHA-256 and size before streaming the validated handle.
- Sanitize attachment filenames, force download/octet-stream/nosniff, never expose stored_path/internal exceptions or parse errors.
- Store new RAW files using content-addressed locations and exclusive writes; preserve existing bytes and compatible legacy records. Failed writes must not register successful storage.
- Cover mismatch/corrupt/path escape/shared RAW/unpublished and safe filename cases with regressions.

## Batch 3 — live integration and final evaluation
### 5. Real HTTP plus actual React browser
- Start owned loopback Django using migrated scratch SQLite and clearly labeled synthetic records (not production data), serve the unchanged published F7 frontend, and exercise real network requests without API interception.
- Test Dashboard -> Detail -> Source Trace -> return, historical selection/reload, preserved zero/exact display/metadata, RAW download, empty/error/refused contexts, responsive/keyboard controls and browser console/network errors.
- Existing FE unit/browser regression suites, build and lint remain separate evidence. No visual redesign or claim of new aesthetic approval.
### 6. Review, repairs, receipts and local checkpoints
- Independent read-only review plus parent inspection. Reproduce findings before minimal repairs; rerun affected tests then final suite.
- Django checks, migration drift check, explicit backend tests, scoped Ruff and browser integration. Preserve actual counts/failures/exit codes/source hashes and known inherited warnings.
- Stage only explicit backend deliverables; verify branch dependency/diff and local commit attribution without changing identity. No push/PR/merge. Preserve recovery data and unrelated worktrees.

## Stop conditions and limits
- No new dependencies, migrations against user DB, real credentials, paid APIs, scheduler/ingestion run, or external state changes without the corresponding authorization.
- Local SQLite evidence is not PostgreSQL/deployment/scalability certification. Synthetic application integration is not official economic-data verification or human visual acceptance.
- If immutable revisions or new financial formulas become necessary instead of explicit unavailability, surface that scope/contract decision rather than silently building a replacement platform.

## Evaluation amendment: exact decimal storage
The real SQLite regression exposed InvalidOperation and binary-float loss at the existing 24-digit field limit. Migration 0004 replaces only Observation.value with a Decimal-compatible field stored as canonical text on SQLite and NUMERIC elsewhere. It is tested on scratch SQLite, not applied to a user DB. Existing precision lost before migration cannot be recovered. All public calculations and comparisons use Python Decimal; SQL numeric ordering/aggregation on the SQLite text representation is not supported by this feature. PostgreSQL execution remains untested.
