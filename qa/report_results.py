"""Summarize an actual full BDD run, without rerunning or grading human acceptance."""
from collections import Counter, defaultdict
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sys


def main():
    run = Path(sys.argv[1]).resolve()
    features = json.loads((run / 'behave.json').read_text(encoding='utf-8'))
    receipt = json.loads((run / 'run.json').read_text(encoding='utf-8'))
    cleanup = json.loads((run / 'cleanup.json').read_text(encoding='utf-8'))
    rows = []
    for feature in features:
        for scenario in feature.get('elements', []):
            if scenario.get('type') != 'scenario':
                continue
            ident = scenario['name'].split(' - ')[0]
            evidence_file = run / ident / 'evidence.json'
            evidence = json.loads(evidence_file.read_text(encoding='utf-8'))
            tags = set(feature.get('tags', []) + scenario.get('tags', []))
            faults = evidence.get('fault_injections', [])
            if 'browser' not in tags:
                layer = 'api-real-view-disposable-db'
            elif any(f['action'] == 'mock-contract' for f in faults):
                layer = 'browser-synthetic-success-contract-NOT-E2E'
            elif faults or evidence.get('storage_fault_injection'):
                layer = 'browser-labelled-fault-injection'
            else:
                layer = 'browser-real-React-Django'
            errors = [step.get('result', {}).get('error_message', 'See full log/evidence')
                      for step in scenario.get('steps', [])
                      if step.get('result', {}).get('status') in ('failed', 'error', 'undefined')]
            rows.append({'id': ident, 'name': scenario['name'], 'status': scenario['status'],
                         'layer': layer, 'evidence': str(evidence_file), 'errors': errors,
                         'human_review_pending': evidence.get('human_review_pending') or evidence.get('acceptance_gate'),
                         'mock_scope': evidence.get('mock_scope'), 'faults': faults,
                         'cleanup': evidence.get('cleanup', {})})
    ids = [r['id'] for r in rows]
    step_counts = Counter(step.get('result', {}).get('status', 'skipped-after-failure')
                          for feature in features for scenario in feature.get('elements', [])
                          if scenario.get('type') == 'scenario' for step in scenario.get('steps', []))
    assert len(ids) == len(set(ids)), 'Duplicate scenario IDs'
    expected = {f'BDD-F{feature:02d}-{case:02d}' for feature in range(1, 9) for case in range(1, 9)}
    expected.update(f'BDD-X-{case:02d}' for case in range(1, 9))
    manifest = receipt.get('suite_manifest')
    overlay = manifest.get('frontend_local_overlay') if manifest else None
    suite_id = receipt.get('suite_id', 'sprint1-baseline-v1')
    if manifest:
        expected = set(manifest['expected_ids'])
        assert len(expected) == 72
        assert not any(fault['action'] == 'mock-contract' for row in rows for fault in row['faults']), 'As-built suite must not use success DTO mocks'
    original = [r for r in rows if r['id'] in expected]
    assert {r['id'] for r in original} == expected, 'The complete selected catalogue is missing scenarios'
    assert len(rows) in (72, 73), 'Unexpected scenario count'
    by_layer = defaultdict(Counter)
    by_feature = defaultdict(Counter)
    for row in original:
        by_layer[row['layer']][row['status']] += 1
        by_feature[row['id'].split('-')[1]][row['status']] += 1
    hashes_match = {}
    qa = Path(__file__).resolve().parent
    for relative, digest in receipt['qa_hashes'].items():
        p = qa / relative
        hashes_match[relative] = p.exists() and hashlib.sha256(p.read_bytes()).hexdigest() == digest
    assert all(hashes_match.values()), 'QA source changed after this receipt'
    if manifest:
        for relative, digest in manifest['feature_hashes'].items():
            assert hashlib.sha256((qa / relative).read_bytes()).hexdigest() == digest, relative
    assert cleanup['disposable_run_directory_removed'], 'Disposable storage not cleaned'
    assert not receipt['external_connections_blocked'], 'Unexpected external network attempt'
    assert all(all(row['cleanup'].values()) for row in rows), 'Owned browser/server cleanup failed'
    assert not any(row['status'] in ('undefined', 'untested') for row in rows), 'Unimplemented scenario remains'
    payload = {
        'generated_at': datetime.now().astimezone().isoformat(), 'run': str(run),
        'suite_id': suite_id,
        'backend_checkpoint': 'd9c673fac84992b91c160bfaa4f0de33a8ce548b',
        'frontend_checkpoint': 'e35d97899d345f18a3341bc19beba431f94179d9',
        'frontend_local_overlay': overlay,
        'catalogue_scenarios': len(original), 'catalogue_status': dict(Counter(r['status'] for r in original)),
        'all_status': dict(Counter(r['status'] for r in rows)),
        'step_status': dict(step_counts),
        'by_layer': {k: dict(v) for k, v in by_layer.items()},
        'by_feature': {k: dict(v) for k, v in by_feature.items()},
        'source_hashes_match': hashes_match, 'cleanup': cleanup, 'scenarios': rows,
        'product_exit_code': receipt['exit_code'], 'driver': 'Chrome/CDP NON-Selenium',
        'visual_approval': 'PENDING', 'contract_acceptance': 'Q01-Q09 remain draft/open; execution is not approval',
        'scope_limit': 'Synthetic fixtures and candidate contracts; not full-SRS conformance, SMTP, official ingestion, production or OS-sandbox proof',
        'acceptance_gaps_retained': manifest.get('remaining_acceptance_gaps', []) if manifest else [],
    }
    markdown = ['# DEKSI — hasil BDD Sprint 1', '',
                f"Run aktual: `{run.name}`. Exit aplikasi: **{receipt['exit_code']}**.", '',
                f"Suite `{suite_id}` — {len(original)} skenario: **{dict(Counter(r['status'] for r in original))}**.",
                f"Termasuk regresi tambahan: **{dict(Counter(r['status'] for r in rows))}**.", '',
                f"Langkah aktual: **{dict(step_counts)}**.", '',
                '## Lapisan bukti', '', '| Lapisan | Hasil |', '|---|---|']
    markdown += [f'| {layer} | {dict(counts)} |' for layer, counts in by_layer.items()]
    markdown += ['', 'Chrome nyata via CDP, bukan Selenium. Kegagalan yang diinjeksi diberi label; respons sukses mock bukan bukti E2E.',
                 'Q02/Q03/Q04 dieksekusi sebagai kontrak kandidat, **bukan persetujuan manusia**. Visual review dan rekonsiliasi SRS lengkap tetap pending.', '',
                 '## Semua skenario', '', '| ID | Status | Lapisan |', '|---|---|---|']
    markdown += [f"| {r['id']} | {r['status'].upper()} | {r['layer']} |" for r in rows]
    if manifest:
        markdown += ['', '## Perubahan cakupan, bukan perbaikan produk', '',
                     'Suite as-built memakai ID baru untuk tiga skenario yang disesuaikan. Baseline acceptance lama tetap tersedia dan tidak dinyatakan lulus oleh hasil ini.']
        markdown += [f"- `{item['baseline']}` → `{item['as_built']}`" for item in manifest['replacements']]
        markdown += ['Kebutuhan acceptance yang belum ditutup:']
        markdown += ['- ' + gap for gap in manifest['remaining_acceptance_gaps']]
    if overlay:
        markdown += ['', '## Perbaikan produk lokal yang diizinkan', '',
                     f"Base FE di atas ditambah overlay belum di-commit pada `{overlay['branch']}`; SHA base tidak memuat perbaikan ini.",
                     'Perubahan source dikunci oleh product_source_hashes dalam suite_manifest run.json.']
        markdown += ['- ' + path for path in overlay['files']]
    markdown += ['', '## Kegagalan aktual', '']
    for row in rows:
        if row['status'] != 'passed':
            markdown += [f"### {row['name']}", f"Status: {row['status']}; lapisan: {row['layer']}."]
            markdown += [f'- {error}' for error in row['errors']]
            markdown += [f"Bukti: `{row['evidence']}`", '']
    markdown += ['## Batas dan keselamatan', '',
                 '- Checkpoint BE: `d9c673fac84992b91c160bfaa4f0de33a8ce548b`.',
                 '- Checkpoint FE: `e35d97899d345f18a3341bc19beba431f94179d9`.',
                 '- Snapshot spesifikasi Batch 1 tidak diedit untuk mengejar PASS; tag historis `@not_run` tidak digunakan sebagai status hasil run.',
                 '- DB, RAW, browser/profile dan port milik pengujian. Email locmem, CSRF asli. Tidak ada provider resmi/AI atau email nyata.',
                 '- Receipt cleanup PASS; hash source QA cocok dengan run. Periksa `boundary-check.json` untuk pemeriksaan port dan Git setelah run.',
                 ('- Perbaikan produk hanya pada overlay FE lokal di atas; tidak ada install, commit, push atau PR. Python audit hook bukan sandbox OS.' if overlay else '- Tidak ada perbaikan produk, install, commit, push atau PR. Python audit hook bukan sandbox OS.'),
                 '- Lihat `../../../FE_HANDOFF.md` untuk reproduksi dan koordinasi frontend yang masih pending.', '']
    for name in ['summary.json', 'summary.md']:
        assert not (run / name).exists(), 'Refuse to overwrite an earlier report'
    (run / 'summary.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    (run / 'summary.md').write_text('\n'.join(markdown), encoding='utf-8')
    print(json.dumps({k: payload[k] for k in ['suite_id', 'catalogue_scenarios', 'catalogue_status', 'all_status', 'by_layer', 'by_feature']}, ensure_ascii=False, indent=2))
    print('REPORT', run / 'summary.md')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
