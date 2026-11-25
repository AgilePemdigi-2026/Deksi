"""Run the combined engine/AI suites using the existing isolated SQLite harness."""
import runpy
from pathlib import Path


def main():
    namespace = runpy.run_path(str(Path(__file__).with_name('run_ai_narrative_sqlite.py')))
    namespace['main'].__globals__['TEST_LABELS'] = (*namespace['TEST_LABELS'],
        'indicators.tests.test_ai_engine_pilot',
        'indicators.tests.test_economic_engine',
        'indicators.tests.test_engine_narrative_preview',
        'indicators.tests.test_engine_ai_integration',
    )
    return namespace['main']()


if __name__ == '__main__':
    raise SystemExit(main())
