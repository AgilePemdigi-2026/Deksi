import copy

from rest_framework import serializers
from django.core.exceptions import ValidationError

from .source_trace import digest, fail, public_revisions, validate_snapshot


def trace_path(revision):
    code = revision.snapshot['indicator']['code']
    return f'/api/v1/indicators/{code}/data-points/{revision.data_point_id}/source-trace/'


class SourceTraceSerializer(serializers.BaseSerializer):
    def to_representation(self, revision):
        validate_snapshot(revision)
        if digest(revision.snapshot) != revision.content_sha256:
            fail()
        snapshot = copy.deepcopy(revision.snapshot)
        missing = []
        for group, names in (
            ('indicator', ('unit',)), ('observation', ('value',)),
            ('source', ('institution_name', 'institution_code', 'publication_name', 'publication_url', 'release_date', 'fetched_at')),
            ('official_value', ('value', 'unit', 'period')), ('identity', ('source_version',)),
        ):
            missing.extend(f'snapshot.{group}.{name}' for name in names if snapshot[group][name] is None)
        warnings = []
        if snapshot['data_origin'] == 'unknown':
            warnings.append({'code': 'data_origin_unrecorded'})
        if snapshot['data_origin'] == 'demo':
            warnings.append({'code': 'demo_data_not_official'})
        calculation = snapshot['calculation']
        if calculation is not None:
            reference_ids = [item['source_revision_id'] for item in calculation['inputs'] if item['source_revision_id']]
            references = {str(row.id): row for row in public_revisions().filter(pk__in=reference_ids)}
            for item in calculation['inputs']:
                reference = references.get(item['source_revision_id'])
                valid = False
                if reference and str(reference.data_point_id) == item['source_data_point_id']:
                    try:
                        validate_snapshot(reference)
                        observation = reference.snapshot['observation']
                        valid = (digest(reference.snapshot) == reference.content_sha256
                                 and (item['value'] is None or item['value'] == observation['value'])
                                 and (item['unit'] is None or item['unit'] == reference.snapshot['indicator']['unit'])
                                 and (item['period'] is None or item['period'] == observation['period']))
                    except ValidationError:
                        valid = False
                if item['source_revision_id'] is not None and not valid:
                    item.update(value=None, source_revision_id=None, source_data_point_id=None)
                    warnings.append({'code': 'formula_input_source_unavailable', 'key': item['key']})
            missing.extend(f'snapshot.calculation.{key}' for key in ('formula_id', 'formula_version', 'expression') if calculation[key] is None)
            if not calculation['inputs']:
                missing.append('snapshot.calculation.inputs')
                warnings.append({'code': 'formula_inputs_unavailable'})
            for index, item in enumerate(calculation['inputs']):
                missing.extend(f'snapshot.calculation.inputs.{index}.{key}' for key in (
                    'label', 'value', 'unit', 'period', 'source_data_point_id', 'source_revision_id'
                ) if item[key] is None)
        root = trace_path(revision)
        previous = public_revisions().filter(source_trace_id=revision.source_trace_id,
                                              data_point_id=revision.data_point_id, sequence__lt=revision.sequence).first()
        previous_url = None
        if previous:
            validate_snapshot(previous)
            if digest(previous.snapshot) != previous.content_sha256:
                fail()
            previous_url = f'{trace_path(previous)}revisions/{previous.id}/'
        return {
            'snapshot': snapshot,
            'publication': {'status': revision.publication_status,
                            'published_at': revision.published_at.isoformat() if revision.published_at else None},
            'metadata': {'status': 'partial' if missing else 'complete', 'missing_fields': sorted(missing),
                         'warnings': warnings, 'verification_status': 'unassessed'},
            'links': {'current': root, 'revision': f'{root}revisions/{revision.id}/',
                      'history': f'{root}revisions/', 'previous_revision': previous_url},
        }
