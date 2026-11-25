"""Prepare an engine explanation locally; send one Gemini request only with exact approval."""
import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from indicators.ai_engine_pilot import (  # noqa: E402
    PROMPT_VERSION, SYSTEM_PROMPT, build_engine_package, gemini_config, generate_engine_narrative,
)
from indicators.ai_narrative_policy import NarrativeError, digest  # noqa: E402
from indicators.ai_narrative_provider import completion_request, strict_json  # noqa: E402


def write_json(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument('--snapshot', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--model', required=True, help='Exact model available in your Gemini project; no automatic fallback')
    parser.add_argument('--workflow-simulated', action='store_true', required=True,
                        help='This pilot accepts only the local preview workflow, not production approval')
    parser.add_argument('--send-once', action='store_true')
    parser.add_argument('--approve-request-sha256')
    parser.add_argument('--acknowledge-api-billing', action='store_true',
                        help='Confirm the API project billing/quota and permission to send this request')
    args = parser.parse_args(argv)
    try:
        snapshot = args.snapshot.resolve(strict=True)
        if snapshot.stat().st_size > 128 * 1024:
            raise ValueError('snapshot_too_large')
        content = snapshot.read_bytes()
        packet = strict_json(content.decode('utf-8'))
        package = build_engine_package(packet, workflow_simulated=True)
        # Validation only. This placeholder key is never transmitted or saved.
        placeholder = gemini_config('local-prepare-only', args.model)
        request = completion_request(placeholder, package, system_prompt=SYSTEM_PROMPT)
        binding = {'snapshotSha256': hashlib.sha256(content).hexdigest(), 'request': request,
                   'promptVersion': PROMPT_VERSION, 'inputDigest': package['inputDigest']}
        request_hash = digest(binding)
        output = args.output_dir.resolve()
        if not args.send_once:
            if args.approve_request_sha256 or args.acknowledge_api_billing:
                raise ValueError('send_flags_require_send_once')
            output.mkdir(parents=True, exist_ok=False)
            write_json(output / 'facts.json', package)
            write_json(output / 'request.json', binding)
            prepared = {'status': 'prepared_no_inference', 'providerPosts': 0,
                'requestSha256': request_hash, 'inputDigest': package['inputDigest'],
                'snapshotSha256': binding['snapshotSha256'], 'model': args.model,
                'promptVersion': PROMPT_VERSION, 'workflowStateSimulated': True,
                'humanApproval': False, 'productionPublication': False}
            write_json(output / 'prepared.json', prepared)
            print(json.dumps(prepared, ensure_ascii=False, indent=2))
            return 0
        if not args.acknowledge_api_billing or args.approve_request_sha256 != request_hash:
            raise ValueError('explicit_request_and_billing_approval_required')
        prepared = strict_json((output / 'prepared.json').read_text(encoding='utf-8'))
        saved_request = strict_json((output / 'request.json').read_text(encoding='utf-8'))
        saved_facts = strict_json((output / 'facts.json').read_text(encoding='utf-8'))
        if (prepared['requestSha256'] != request_hash or digest(saved_request) != request_hash
                or saved_request != binding or saved_facts != package):
            raise ValueError('prepared_request_changed')
        key = os.environ.get('GEMINI_API_KEY', '')
        if not key:
            raise ValueError('GEMINI_API_KEY_missing_do_not_paste_it_into_chat')
        config = gemini_config(key, args.model)
        # Minimal settings only; never import production settings, .env or the ORM.
        from django.conf import settings
        if not settings.configured:
            settings.configure(DATABASES={'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}},
                               SECRET_KEY='local-pilot-no-auth')
        state = {'status': 'dispatch_reserved_outcome_unknown_until_result', 'providerPosts': 'at_most_one',
                 'requestSha256': request_hash, 'model': args.model,
                 'reservedAt': datetime.now(timezone.utc).isoformat(), 'automaticRetry': False}
        # Exclusive reservation before network. A timeout/crash never permits blind replay in this directory.
        write_json(output / 'dispatch-once.json', state)
        raw_hash = None

        def preserve_response(raw):
            nonlocal raw_hash
            if key.encode() in raw:
                raise NarrativeError('invalid_output')
            with (output / 'response-original.bin').open('xb') as stream:
                stream.write(raw)
            raw_hash = hashlib.sha256(raw).hexdigest()

        try:
            result, reported_model = generate_engine_narrative(config, package, response_sink=preserve_response)
            record = {**state, 'status': 'valid_contract_human_review_pending', 'providerPosts': 1,
                      'reportedModel': reported_model, 'responseSha256': raw_hash, 'narrative': result,
                      'humanApproval': False, 'productionPublication': False}
            write_json(output / 'result.json', record)
            print(json.dumps(record, ensure_ascii=False, indent=2))
            return 0
        except NarrativeError as error:
            record = {**state, 'status': error.code, 'responseSha256': raw_hash,
                      'humanApproval': False, 'productionPublication': False}
            write_json(output / 'result.json', record)
            print(json.dumps(record, ensure_ascii=False, indent=2))
            return 1
    except (OSError, ValueError, TypeError, KeyError, UnicodeError, RecursionError):
        # Never print exception text: it can include credential-bearing provider or filesystem input.
        print(json.dumps({'status': 'local_preflight_refused', 'automaticRetry': False,
                          'help': 'Check snapshot, explicit model, prepared request digest, billing acknowledgement, key environment and existing dispatch marker.'}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
