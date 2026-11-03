# F6 — public detail API backend

Branch: `feat/6-detail-indikator-be`. Base: main `0e92899ce54f85440fe920ca457dfd91f747e1aa` (not the older `be` scaffold).

## Contract

- Existing public GET `/api/indicators/?code=<code>` and `/api/indicators/<code>/trend/` remain compatible with the published React frontend. Source Trace remains the inherited dependency until F7's focused delta.
- Only `published` observations with both recorded reviewer and review time are public. Missing indicator/empty database remain explicit; public requests require no login.
- Previous-value comparison and sparklines require the same indicator, source, unit, frequency and measurement type. Percent-unit differences are percentage points; other units use `(current - previous) / abs(previous) * 100` and explicitly named previous period. Zero denominators are unavailable. Decimal display rounding is two places; direction means numerical direction, not economic benefit.
- Native trend rows preserve metadata and expose `exactValue` alongside the legacy approximate numeric graph value. Annual/monthly aggregations use Decimal; unlike series and cumulative-YTD sum aggregation are rejected with 400. Mixed native rows remain available for the frontend's labelled table; a mixed-series average is unavailable.
- Success/error JSON is `Cache-Control: no-store`. No provider or source-link network calls occur on these reads.

## Precision migration

`0004_exact_observation_decimal` stores the same 24-digit/6-decimal domain without SQLite NUMERIC/float conversion. Django forms and Python values remain Decimal. SQLite SQL value ordering/aggregation is not an exact numeric contract; this code performs those operations in Python. Other engines use native NUMERIC, but PostgreSQL was not executed in this delivery. A migration cannot recover precision lost by earlier SQLite writes. Back up and review an actual deployment database before applying; none was opened here.

## Reproduce (isolated tests)

Use a compatible interpreter and `backend/requirements.txt` (which includes the root manifest and the actual API imports). No new packages were installed for this delivery; the existing compatible Login interpreter was used read-only.

```
python manage.py test indicators.tests --settings=backend.test_settings_indicators
python manage.py check --settings=backend.test_settings_indicators
python manage.py makemigrations --check --dry-run --settings=backend.test_settings_indicators
ruff check indicators/views.py indicators/models.py indicators/fields.py indicators/tests indicators/migrations/0004_exact_observation_decimal.py backend/test_settings_indicators.py
```

Test settings never read `.env` and default to an in-memory SQLite test DB. Fixtures explicitly use `UJI SINTETIS`. Source-data accuracy, immutable revisions, official verification and production deployment are separate acceptance gates; no fake formula/input/version or AI output is generated. See [plan](PLAN.md) and `VERIFICATION.json` for actual local evidence.
