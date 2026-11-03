# Audit repairs 1–4 — scoped two-batch plan

User authorized fixes 1–2 then 3–4. No commit, push, PR, merge, dependency/model/provider change or ingestion lifecycle change in this repair stage.

## Baselines and ownership
- F6 BE 652ec018ddad455358a9d552593c11b52c4be03b; F7 BE a9c6367b7077341a0ae43276463fbd08546a5c28.
- F6 FE 13a7680e96c1170cb9dcc041577e626760d8d76f; F7 FE 94a05cd1fe5044d3d7e0f71ad6d0487edd5f921f.
- Use each existing isolated worktree, preserve its feature-specific wiring, apply shared corrections to both relevant lanes. Published branches and historical checkpoints remain untouched.

## Batch 1: findings 1–2
1. Keep exact decimal storage; replace the raw sortable Admin value column with an explicit non-sortable exact display. Test actual Admin header and crafted ordering query so this is not merely hiding a link. Do not add a float SQL cast. Numeric SQL operations on SQLite text remain unsupported outside this display contract.
2. Validate/prefer exactValue for history strings; use number conversion only to check consistency/plot geometry. Preserve legacy payload support, null/zero distinction and independent-resource error handling. Add regressions for large/negative/fine decimal values and malformed/inconsistent exact/numeric pairs.

## Batch 2: findings 3–4
3. Carry sourceId through history types/adapter; reject drawing mixed known/unknown/different sources and retain original labelled table rows. Keep existing frequency/type/unit guards.
4. Split regular calendar series at missing/out-of-order/duplicate periods using actual valid dates and monthly/quarterly/semiannual/annual cadence. Never manufacture a zero/observation. Do not invent a daily business calendar or apply cadence to adhoc data. Preserve explicit null-gap behavior and original input.

## Acceptance and verification
- Obtain targeted RED before each production repair and save logs, then GREEN. Test and copy only shared corrections; verify no F7 wiring is overwritten.
- Backend test DB only, explicit HERMES_TEST_SCRATCH, no .env or user DB. Existing interpreter and dependencies only.
- Run standalone F6 and combined F7 backend tests/checks/migration drift/scoped lint; explicit F6/F7/shared frontend suites, build/lint, and browser checks on both lanes.
- Extend actual FE→Django loopback checks for exact large history display, source refusal and calendar-gap rendering. Keep synthetic data, real API/no-interception, and cleanup proofs explicit.
- Report actual counts, skipped physical symlink test and inherited warnings separately. Previous readiness receipts are historical after these source changes. Persist a new repair receipt, not a fabricated canonical-verification claim.
- Additional inherited ingestion/last-valid issue is out of scope; no production-ready claim or automatic publication gate advancement.
