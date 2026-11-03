# Final evaluation — backend F6/F7

> Historical checkpoint evaluation. Later audit repairs and canonical-verification results are described in [CURRENT_STATUS.md](CURRENT_STATUS.md). Counts and canonical-unverified statements below are retained as history, not the current readiness verdict. Batch 1 importer/review lifecycle remains deferred.

Evaluated locally on 2026-11-03. No push/PR/merge. F6 remains a standalone backend branch; F7 inherits its verified checkpoint and contains the Source Trace delta only.

## Findings repaired with executed regressions

1. Unreviewed `published` values were visible. The shared public query and RAW route now require recorded reviewer and review time.
2. Comparisons/sparklines mixed sources, units, measurement types and frequencies. They now use a comparable series; percent-unit changes are explicit percentage points; zero-denominator relative changes remain unavailable.
3. SQLite NUMERIC/float conversion lost precision and raised `InvalidOperation` at the declared 24-digit limit. The scoped field/migration preserves exact values, with a 24-digit-boundary round-trip and forward-migration test. Previously lost precision cannot be recovered; SQLite SQL numeric sorting/aggregation is not promised.
4. Native history/annual aggregation mixed incompatible semantics or used binary float arithmetic. Original metadata and an exact decimal string are preserved; incompatible derived aggregation is refused rather than invented.
5. Trace rows lost their own RAW metadata when sharing a checksum; that deduplication was removed. Exact selectors reject missing context instead of newest fallback; history slicing is bounded before serialization and pagination totals are explicit.
6. RAW could reference another source, leave the configured root, be overwritten by a later document using the same filename, exceed memory bounds or produce unsafe attachment headers. Source binding, root/link checks, bounded size/hash verification, validated-byte streaming, safe headers and exclusive content-addressed storage address these paths.
7. A repair's failed-open cleanup could remove a preexisting file. A separate RED test reproduced this; cleanup now applies only after this call successfully created the file.
8. Source history performed per-row Indicator queries. The regression now enforces four queries for the fixture rather than nine.
9. Harness safety/runtime attribution were corrected: final tests explicitly allocate permitted scratch paths, clean task-owned failed probes, and report the actually verified Python 3.14.7 runtime rather than inferring another venv's version.

## Final executed evidence (not additive totals)

| Check | Actual result |
|---|---|
| F6 standalone backend | 18 tests PASS |
| Combined F6+F7 backend | 39 tests executed: 38 PASS, 1 skipped |
| Skip | Physical Windows symlink creation lacks required privileges; not reported as PASS |
| Django check | No issues |
| Migration drift | No changes detected |
| Ruff on all scoped Python code/tests | PASS |
| Node syntax check for integration harness | PASS |
| Published frontend unit suites | F6 33, F7 12, editorial 7 PASS (52 total) |
| Published frontend build | PASS; existing >500 kB chunk warning |
| Published frontend lint | Exit 0; three existing warnings |
| Actual React → Django browser integration | Eight check groups PASS, no API interception and no browser exceptions |
| Cleanup | Owned browser profile, synthetic DB/RAW directory removed; owned Django/browser stopped |
| Independent current-code review | No additional blocking finding confirmed within the six inspected files; static review only, not an extra test suite |

The real browser run checks Dashboard → Detail → Source Trace → back, keyboard selection/reload of a history row outside the previous 12-row limit, exact displayed decimals and zero, shared RAW, safe text rendering, actual cross-origin download digest, disk-corruption HTTP 503, actual stored-value mutation refusing an old guard, empty/malformed paths and 390/768/1440 widths. Database fixtures are prominently labelled UJI SINTETIS; this is real application integration, not official-data verification.

## Acceptance limits

- No provider/API acquisition, user-database migration, official economic-data verification, PostgreSQL run, deployment or new human visual approval was performed.
- Legacy observations/source masters remain mutable, not immutable revision storage. Missing versioned formulas/inputs and official verification stay explicitly unavailable; this delivery does not manufacture them or redesign the ingestion/Admin review lifecycle.
- The published FE reads the default bounded source-history page; the new backend exact-selector/pagination API is not a claim that the old FE has unlimited history or new formula/revision UI.
- Canonical Hermes's generic test recipe continued selecting the global Python without Django even with a process-local environment attempt. Those failed recipe logs are preserved separately. The explicit project-interpreter test commands, current source hashes and real loopback run are the application evidence; installation/ledger/config changes were not used to silence recognition.

See `VERIFICATION.json` for hashes, exact reproduction commands, review scope and current local dependency. Detailed local logs/screenshots remain under ignored `backend/.artifacts/`; a post-checkpoint publication-readiness receipt identifies the actual commits. Ready for a later authorized feature-branch push is not approval to merge or deploy.
