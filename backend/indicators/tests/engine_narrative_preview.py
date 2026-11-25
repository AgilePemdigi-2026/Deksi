"""Strict read-only reader for saved Gemini output, used only by the loopback preview."""
import hashlib
import json
import re
from datetime import datetime


METRICS = {'pmtb_share', 'household_consumption_share'}


def _digest(value):
    raw = json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(',', ':'), allow_nan=False)
    return hashlib.sha256(raw.encode()).hexdigest()


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError('duplicate_preview_json_key')
        result[key] = value
    return result


def _json(raw):
    return json.loads(raw.decode('utf-8'), object_pairs_hook=_pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError('invalid_json_constant')))


def _read(path):
    if path.stat().st_size > 128 * 1024:
        raise ValueError('preview_artifact_too_large')
    return path.read_bytes()


def load_preview_narrative(directory, snapshot):
    """Return the exact archived packet and an allowlisted, explicitly unreviewed narrative."""
    packet_raw = _read(snapshot)
    packet = _json(packet_raw)
    request = _json(_read(directory / 'request.json'))
    prepared = _json(_read(directory / 'prepared.json'))
    facts = _json(_read(directory / 'facts.json'))
    result = _json(_read(directory / 'result.json'))
    raw = _read(directory / 'response-original.bin')
    envelope = _json(raw)
    request_digest = _digest(request)
    if (hashlib.sha256(packet_raw).hexdigest() != request['snapshotSha256']
            or prepared['snapshotSha256'] != request['snapshotSha256']
            or any(record['requestSha256'] != request_digest for record in (prepared, result))
            or request['inputDigest'] != facts['inputDigest']
            or facts['inputDigest'] != _digest({key: value for key, value in facts.items() if key != 'inputDigest'})
            or _json(request['request']['messages'][1]['content'].encode()) != facts
            or request['promptVersion'] != facts['promptVersion']
            or result['responseSha256'] != hashlib.sha256(raw).hexdigest()
            or result['status'] != 'valid_contract_human_review_pending'
            or result['providerPosts'] != 1 or type(result['providerPosts']) is not int
            or result['humanApproval'] is not False or result['productionPublication'] is not False
            or facts['workflowStateSimulated'] is not True
            or set(packet['metrics']) != METRICS or set(facts['metrics']) != METRICS):
        raise ValueError('saved_narrative_binding_mismatch')
    model = result['model']
    if (not re.fullmatch(r'gemini-[A-Za-z0-9_.-]{1,100}', model)
            or any(record['model'] != model for record in (prepared, envelope, request['request']))
            or result['reportedModel'] != model or len(envelope['choices']) != 1
            or envelope['choices'][0]['finish_reason'] != 'stop'
            or _json(envelope['choices'][0]['message']['content'].encode()) != result['narrative']):
        raise ValueError('saved_narrative_original_response_mismatch')
    narrative = result['narrative']
    if (set(narrative) != {'summary', 'meaning', 'comparison', 'limitations', 'factRefs'}
            or narrative['comparison'] is not None
            or sorted(narrative['factRefs']) != sorted('metrics.' + name for name in METRICS)
            or any(type(narrative[key]) is not str or not narrative[key].strip() or len(narrative[key]) > 600
                   for key in ('summary', 'meaning', 'limitations'))):
        raise ValueError('saved_narrative_contract_mismatch')
    bindings, review_times = {}, set()
    for name in sorted(METRICS):
        metric, fact = packet['metrics'][name], facts['metrics'][name]
        if (metric['available'] is not True or metric['period'] != facts['period']
                or metric['observationDate'] != facts['observationDate']
                or metric['value'] != fact['value'] or metric['unit'] != fact['unit']
                or metric['methodVersion'] != fact['methodVersion']
                or metric['formula'] != fact['formula'] or metric['formulaVersion'] != fact['formulaVersion']
                or metric['priceBasis'] != facts['priceBasis'] or metric['revisionStatus'] != facts['revisionStatus']
                or metric['resultDigest'] != fact['resultDigest'] or metric['inputDigest'] != fact['sourceInputDigest']
                or metric['resultDigest'] != _digest({key: value for key, value in metric.items() if key != 'resultDigest'})
                or set(metric['inputs']) != set(fact['inputs'])):
            raise ValueError('saved_narrative_engine_mismatch')
        for code, item in metric['inputs'].items():
            expected = fact['inputs'][code]
            projection = {key: item[key] for key in ('value', 'unit', 'publicationDate', 'evidenceChecksumSha256')}
            projection['source'] = item['sourceId']
            if projection != expected:
                raise ValueError('saved_narrative_source_mismatch')
            review_times.add(item['trace']['reviewedAt'])
        bindings[name] = {key: metric[key] for key in ('value', 'unit', 'inputDigest', 'resultDigest')}
    if len(review_times) != 1:
        raise ValueError('simulated_review_time_ambiguous')
    reviewed_at = next(iter(review_times))
    if datetime.fromisoformat(reviewed_at).utcoffset() is None:
        raise ValueError('simulated_review_time_requires_timezone')
    payload = {'schemaVersion': 'deksi.local-engine-narrative.v1', 'status': 'draft_preview',
               'model': model, 'period': facts['period'], 'metricsBinding': bindings,
               'humanApproval': False, 'productionPublication': False, 'workflowStateSimulated': True,
               'requestSha256': request_digest, 'responseSha256': result['responseSha256'], 'narrative': narrative}
    return packet, payload, reviewed_at
