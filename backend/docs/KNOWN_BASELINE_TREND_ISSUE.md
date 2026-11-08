# Known inherited trend-aggregation defect (not an auth regression)

Status: OPEN, NOT FIXED by Login Admin work. Discovered by an additional public-route auth regression probe.

Baseline: `0e92899ce54f85440fe920ca457dfd91f747e1aa`. `git diff BASE -- backend/indicators` is empty on `feat/1-login-admin-be`; auth changes did not introduce the indicator code below.

## Executed reproduction
- Django test database only: create a synthetic `pdb` indicator, synthetic source, and one PUBLISHED observation dated 2020-01-01, period `2020`, frequency `annual`, data type `level`, value 1.25.
- Anonymous GET `/api/indicators/pdb/trend/` raises `NameError: name 'values' is not defined`.
- The same fixture's Source Trace subcase did not fail. The successful earlier auth suite had 44 tests before this extra probe; the expanded run had 47 tests with this one error.
- Failed full-run evidence retained at ignored `.test-artifacts/auth_suite-final.txt`. Do not replace that log with a passing run or promote this observation to a fixed defect.

## Source trace
- `indicators/views.py:239-245`: GRANULARITY_LABELS has no `annual` entry even though the model permits that frequency.
- `indicators/views.py:347-368`: the default annual term does not match the native-label branch and falls through to monthly aggregation.
- `indicators/views.py:317-325`: monthly aggregation refers to `values` without binding it in the comprehension. This is also a source-backed risk for actual daily-to-monthly aggregation; that separate daily-input reproduction was not executed here.

## Auth verification boundary
The auth-only public-route control uses a synthetic quarterly PDB observation, with native and explicit yearly requests plus Source Trace. This changes only this newly authored test fixture to isolate authorization; no response/status assertion is weakened and no indicator implementation changes. Passing auth tests do not establish correctness of all aggregation modes or real economic data.

Repair requires a separate scoped indicator-backend change and regression tests against supported frequency/aggregation semantics. Do not patch this financial calculation silently in the Admin login branch.
