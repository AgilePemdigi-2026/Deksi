"""Opt-in disposable server for real browser->Django narrative QA with fake model transport."""
import json
import os
from datetime import date
from decimal import Decimal
from pathlib import Path
from wsgiref.simple_server import make_server


def main():
    if os.environ.get('DEKSI_AI_BROWSER_TEST') != '1':
        raise RuntimeError('Only the explicit disposable browser runner may start this fixture')
    scratch = Path(os.environ['HERMES_TEST_SCRATCH']).resolve()
    database = Path(os.environ['DEKSI_TEST_DATABASE']).resolve()
    if (not database.is_relative_to(scratch) or not database.parent.name.startswith('deksi-ai-browser-')
            or database.exists()):
        raise RuntimeError('Fixture requires a fresh task-owned scratch database')
    database.parent.mkdir(parents=True, exist_ok=True)
    os.environ['DJANGO_SETTINGS_MODULE'] = 'backend.test_settings_indicators'
    from django.conf import settings
    settings.INSTALLED_APPS = [*settings.INSTALLED_APPS, 'admin_auth']
    settings.ROOT_URLCONF = __name__
    settings.DEKSI_RAW_DIR = database.parent / 'raw'
    settings.DEKSI_AI_NARRATIVES_ENABLED = True
    settings.LLM_BASE_URL = 'http://127.0.0.1:11434/v1'
    settings.LLM_MODEL = 'synthetic:1'
    settings.LLM_API_KEY = ''
    import django
    django.setup()
    import httpx
    from django.contrib.auth import get_user_model
    from django.contrib.auth.models import Permission
    from django.core.exceptions import PermissionDenied
    from django.core.management import call_command
    from django.core.wsgi import get_wsgi_application
    from django.http import JsonResponse
    from django.urls import include, path
    from django.utils import timezone
    from django.views.decorators.http import require_GET, require_POST

    from indicators import ai_narrative as service
    from indicators.models import AINarrativeDraft, AINarrativeReview, Indicator, Observation, Source
    from indicators.storage import save_raw

    state = {'calls': 0}

    @require_GET
    def health(_request):
        return JsonResponse({'fixture': 'synthetic-narrative-only', 'ready': True})

    @require_POST
    def control(request):
        try:
            service.authorize(request.user, service.GENERATE_PERMISSION)
        except PermissionDenied:
            return JsonResponse({'error': 'Test fixture permission denied'}, status=403)
        body = json.loads(request.body)
        mode = body.get('mode')
        if mode in ('process', 'timeout'):
            def handle(_request):
                state['calls'] += 1
                if mode == 'timeout':
                    raise httpx.ReadTimeout('Synthetic ambiguous delivery')
                output = {'summary': 'Kegiatan ekonomi dibandingkan dengan periode tahunan sebelumnya.',
                    'meaning': 'PDB menggambarkan ukuran kegiatan ekonomi, bukan pendapatan setiap keluarga.',
                    'comparison': None, 'limitations': 'Penyebab perubahan tidak dapat disimpulkan dari angka ini.',
                    'factRefs': ['facts.current']}
                return httpx.Response(200, json={'model': 'synthetic:1', 'choices': [
                    {'finish_reason': 'stop', 'message': {'role': 'assistant', 'content': json.dumps(output)}}]})
            service.run_once(transport=httpx.MockTransport(handle))
        elif mode == 'change':
            Observation.objects.filter(indicator__code='pdb').update(value=Decimal('6'))
        elif mode != 'counts':
            return JsonResponse({'error': 'Unknown fixture operation'}, status=400)
        return JsonResponse({'calls': state['calls'], 'drafts': AINarrativeDraft.objects.count(),
            'reviews': AINarrativeReview.objects.count(),
            'value': str(Observation.objects.get(indicator__code='pdb').value)})

    global urlpatterns
    urlpatterns = [path('api/__ai-fixture/health/', health), path('api/__ai-fixture/control/', control),
                   path('', include('backend.urls'))]
    call_command('migrate', verbosity=0, interactive=False)
    user = get_user_model().objects.create_user(username='ai-browser-synthetic',
        password=os.environ['DEKSI_AI_BROWSER_PASSWORD'], is_staff=True)
    user.user_permissions.set(Permission.objects.filter(content_type__app_label='indicators', codename__in=(
        'generate_ainarrativedraft', 'review_ainarrativedraft', 'view_ainarrativedraft',
        'change_observationcandidate')))
    source = Source.objects.get(source_id='BPS')
    source.source_name = 'BPS UJI SINTETIS'
    source.save(update_fields=['source_name'])
    indicator = Indicator.objects.create(code='pdb', name='PDB UJI SINTETIS', category='Test', unit='%')
    raw, _ = save_raw(source, b'SYNTHETIC BROWSER EVIDENCE', 'synthetic.json')
    Observation.objects.create(indicator=indicator, source=source, raw_file=raw,
        observation_date=date(2025, 6, 30), period_label='Q2 2025', frequency='quarterly', data_type='yoy',
        value=Decimal('5.123456'), unit='%', validation_status='published', reviewed_by=user,
        reviewed_at=timezone.now())
    with make_server('0.0.0.0', 8080, get_wsgi_application()) as server:
        print('SYNTHETIC narrative browser fixture ready', flush=True)
        server.serve_forever()


if __name__ == '__main__':
    main()
