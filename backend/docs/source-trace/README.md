# F7 — public Source Trace backend

> Current working-tree status, reviewed-candidate lifecycle and remaining publication gates: [CURRENT_STATUS.md](CURRENT_STATUS.md). Earlier `VERIFICATION.json` and `EVALUATION.md` remain historical receipts.

Branch: `feat/7-source-trace-be`, currently inheriting corrected F6 checkpoint `032b9aec4de0a5d9d96fe94b638329ab5207b586`; the later lifecycle overlay is not yet committed. This is a backend delta over the actual React-compatible `main` tree, not the old `be` scaffold. No push, PR or merge is part of this local delivery.

## Public HTTP contract

- `GET /api/indicators/<code>/source-trace/` returns the latest reviewed, published observation, with each history row retaining its own source/RAW metadata even when several rows share the same document checksum. Unknown indicators return 404; existing empty indicators return `available: false`. Public access requires no account.
- Optional exact selection requires all four parameters: `observationDate=YYYY-MM-DD`, `frequency`, `dataType`, `sourceId`. Missing/invalid/repeated/unknown parameters return 400; missing exact context returns 404 rather than silently selecting newest. Ambiguity returns 409.
- `limit` defaults to 100, maximum 100; `offset` defaults to 0. `pagination` contains actual `offset`, `limit`, `total`, `hasMore`. Selection is independent of page position. The published frontend currently reads the default page only; this is not a claim of unlimited frontend history/pagination.
- Decimal values are strings. Observation period, date-only release, RAW acquisition and recorded review are distinct. No reviewer identity, validation notes, parse errors or filesystem path is returned.
- `observationId` is a live model identity, **not** a revision identifier. `revisionId: null`, `immutableSnapshot: false`, `officialVerification: unassessed`, and unavailable formula/input fields explicitly describe the current storage limit. `derived_sum` is a known derived type; other types remain unclassified instead of being asserted official.
- Unsafe/non-HTTP(S)/credential-bearing URLs become null. Source URLs are metadata only; these APIs never fetch them. A RAW from a different source is not projected or downloadable under this observation.

## RAW download and storage

`GET /api/indicators/<code>/raw-file/<id>/` requires a reviewed published indicator/RAW/source relationship. It restricts existing paths to `DEKSI_RAW_DIR`, rejects non-files and filesystem links, bounds the read by `DEKSI_MAX_RAW_BYTES` (32 MiB default), and verifies actual byte length and SHA-256. Missing/denied/escaped files return 404; size/checksum corruption returns 503. The response streams the already-validated in-memory bytes, with sanitized attachment filename, octet-stream, nosniff and no-store headers. Checksums prove byte integrity, not factual correctness.

New writes use source-primary-key/content-hash paths and exclusive creation, not a mutable original filename. Identical content reuses validated existing storage without changing its metadata; corruption is refused rather than overwritten. Failed open cannot remove a preexisting RAW. Legacy valid stored paths within the configured root remain readable. This is an application trust boundary, not an OS sandbox or protection against a privileged concurrent filesystem/database administrator. Multi-process writer-race guarantees were not exercised.

## Reproduce backend checks

Use the existing compatible Python and declared `backend/requirements.txt`. Set `HERMES_TEST_SCRATCH` to an explicitly permitted scratch directory. Do not copy a user `.env` or restore production database backups for tests.

```
python manage.py test indicators.tests --settings=backend.test_settings_indicators
python manage.py check --settings=backend.test_settings_indicators
python manage.py makemigrations --check --dry-run --settings=backend.test_settings_indicators
ruff check indicators/storage.py indicators/tests/test_import_raw_safety.py indicators/admin.py indicators/tests/test_admin_exact_value.py indicators/models.py indicators/lifecycle.py indicators/ingest.py indicators/bps.py indicators/fiscal.py indicators/management/commands/publish_observations.py indicators/management/commands/fetch_kemenkeu.py indicators/management/commands/ingest_datasets.py indicators/management/commands/sync_bps.py indicators/migrations/0005_observation_candidate.py indicators/tests/test_import_lifecycle.py indicators/tests/test_import_writers.py indicators/tests/test_candidate_review.py indicators/tests/test_import_command_logs.py indicators/tests/test_lifecycle_transactions.py
```

## Actual frontend integration

Use the separate `feat/7-source-trace-fe` worktree based on `94a05cd1fe5044d3d7e0f71ad6d0487edd5f921f`, including its local exact-value/source/calendar-gap companion repairs and existing dependencies. Those repairs are not yet published. The backend branch's inherited frontend is not that feature frontend. Run from `backend/`:

```
python indicators/tests/run_frontend_integration.py --frontend-root <absolute-feature-7-frontend-directory>
```

The runner requires existing Node/Vite and Chrome, free loopback ports 8000 and 5196, and `HERMES_TEST_SCRATCH`. It migrates a fresh owned SQLite DB, seeds clearly marked UJI SINTETIS records, starts real Django and the paired React working tree, and uses a disposable browser without API interception. It additionally stages/rejects candidates, injects a publication-log failure to exercise rollback, and publishes only a selected candidate through the actual authorized Admin CLI. Public data/RAW must remain available before review and old FE guards must refuse changed context afterward. It exercises public Dashboard → Detail → Source Trace → return, historical selection/reload beyond the old 12-row window, exact display/zero, shared RAW, safe text rendering, browser/CORS download digest, actual disk-corruption refusal, actual DB-value-change context refusal, empty/malformed routes and 390/768/1440 layouts. Successful and failed checks are kept separately in `.artifacts/`; no source-site acquisition occurs. Only task-owned fixture values/files are mutated, then the DB/profile and owned processes are cleaned up.

The paired FE's unit suites/build/lint are also run separately. Runtime/network integration does not prove human visual approval, official economic-data correctness, ingestion correctness or production readiness. The later shared [candidate lifecycle](../indicator-detail/LIFECYCLE.md) protects public rows during importer staging and requires explicit review before replacement. This is not immutable revision storage or versioned formula/input storage. Once an authorized candidate replaces a live observation, the old value is not exposed as a preserved public historical revision; the FE context guard refuses changed content rather than fabricating a snapshot.

See [F6 foundation](../indicator-detail/README.md), [scoped plan](../indicator-detail/PLAN.md), and [current status](CURRENT_STATUS.md) for evidence boundaries and remaining gates. The original `VERIFICATION.json` retains its checkpoint's commands, hashes and counts. The earlier generic-Python recognition failure has since been resolved by authorized worktree-local recipes: canonical results and exact root/session ledger readback passed. These recipes intentionally perform no bootstrap installation or standalone start/readiness phase; the real loopback run supplies separate exercised-runtime evidence.
