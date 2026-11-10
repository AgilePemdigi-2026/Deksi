"""Frontend-owned isolated integration runner; backend dependency is read-only."""
import argparse
import calendar
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from datetime import date
from decimal import Decimal
from pathlib import Path

FRONTEND = Path(__file__).resolve().parents[1]
BACKEND = Path('E:/Deksi-Team/.hermes/worktrees/sprint-1-dashboard-be/backend')
SCRATCH = Path(os.environ['HERMES_TEST_SCRATCH']).resolve()
OUTPUT = FRONTEND / '.artifacts' / 'sprint-1' / 'live'


def configure():
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(BACKEND))
    os.environ['DJANGO_SETTINGS_MODULE'] = 'backend.test_settings_indicators'
    os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
    import django
    django.setup()


def seed(presentation=False):
    from django.contrib.auth import get_user_model
    from django.utils import timezone
    from indicators.models import Indicator, Observation, Source
    from indicators.storage import save_raw
    user = get_user_model().objects.create_user(username='UJI_SYNTHETIC_REVIEW', is_staff=True)
    source = Source.objects.create(source_id='TEST_ONLY', source_name='Dataset UJI SINTETIS',
        institution='INSTANSI UJI SINTETIS', primary_url='https://example.test/source')
    raw, _ = save_raw(source, b'UJI SYNTHETIC RAW - NOT OFFICIAL', 'UJI.txt',
        source_url='https://example.test/document', period_label='UJI 2024-2025')
    units = {'pdb':'%', 'inflasi':'%', 'fiskal':'Rp Triliun', 'investasi':'Rp Triliun', 'birate':'%', 'tpt':'%'}
    types = {'pdb':'yoy', 'inflasi':'yoy', 'fiskal':'cumulative_ytd', 'investasi':'derived_sum', 'birate':'level', 'tpt':'level'}
    for code, unit in units.items():
        indicator = Indicator.objects.create(code=code, name=code.upper()+' UJI SINTETIS', category='UJI', unit=unit)
        if code == 'tpt':
            continue
        for year, month, value in [(2024,1,'2.123456'),(2024,3,'3.123456'),(2025,1,'0')]:
            if code == 'pdb':
                value = ({(2024,1): '4.90', (2024,3): '5.05', (2025,1): '5.12'}[(year,month)]
                         if presentation else '999999999999999999.999999')
            if code in ['investasi', 'fiskal']:
                value = '32.5' if year == 2025 else '21.5'
            Observation.objects.create(indicator=indicator, source=source, raw_file=raw,
                observation_date=date(year,month,calendar.monthrange(year,month)[1]),
                period_label=f'UJI {year}-{month:02}', frequency='monthly', data_type=types[code],
                value=Decimal(value), unit=unit, publication_date=date(year,month,1),
                validation_status='published', reviewed_by=user, reviewed_at=timezone.now())
    return {'synthetic':True, 'raw_path':raw.stored_path, 'raw_checksum':raw.checksum_sha256,
            'raw_url':f'/api/indicators/inflasi/raw-file/{raw.pk}/'}


def inspect_feedback():
    database = Path(os.environ['DEKSI_TEST_DATABASE']).resolve()
    assert database.is_relative_to(SCRATCH) and database.parent.name.startswith('deksi-b2-live-')
    configure()
    from indicators.feedback_model import Feedback
    rows=list(Feedback.objects.values('category','description','status','admin_notes','sender_name','sender_email'))
    print(json.dumps({'rows':rows}))


def run():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for port in [56120,56121]:
        with socket.socket() as listener:
            listener.bind(('127.0.0.1',port))
    with tempfile.TemporaryDirectory(dir=SCRATCH, prefix='deksi-b2-live-') as temporary:
        owned=Path(temporary)
        os.environ['DEKSI_TEST_DATABASE']=str(owned/'qa.sqlite3')
        os.environ['DEKSI_TEST_RAW_ROOT']=str(owned/'raw')
        os.environ['DEKSI_PUBLIC_API_TARGET']='http://127.0.0.1:56121'
        os.environ['DEKSI_QA_FRONTEND']=str(FRONTEND)
        os.environ['DEKSI_QA_OUTPUT']=str(OUTPUT)
        os.environ['DEKSI_QA_PYTHON']=sys.executable
        os.environ.pop('PYTHONPATH',None)
        os.environ.pop('PYTHONHOME',None)
        configure()
        from django.core.management import call_command
        call_command('migrate',interactive=False,verbosity=0)
        fixture=seed()
        fixture_path=owned/'fixture.json'
        fixture_path.write_text(json.dumps(fixture))
        os.environ['DEKSI_QA_FIXTURE']=str(fixture_path)
        log=(OUTPUT/'django.log').open('w',encoding='utf-8')
        server=subprocess.Popen([sys.executable,'-B',str(BACKEND/'manage.py'),'runserver','127.0.0.1:56121',
            '--noreload','--settings=backend.test_settings_indicators'],cwd=owned,
            env=os.environ.copy(),stdout=log,stderr=subprocess.STDOUT)
        code=1
        try:
            for _ in range(100):
                if server.poll() is not None:
                    raise RuntimeError('Owned backend exited; inspect django.log')
                try:
                    with urllib.request.urlopen('http://127.0.0.1:56121/api/indicators/',timeout=1) as response:
                        if response.status==200:
                            break
                except OSError:
                    time.sleep(.1)
            else:
                raise RuntimeError('Owned Django did not become ready')
            result=subprocess.run(['node',str(FRONTEND/'tests/dashboard.browser.mjs')],cwd=FRONTEND,
                env=os.environ.copy(),timeout=240)
            code=result.returncode
        finally:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill();server.wait(timeout=5)
            log.close()
            from django.db import connections
            connections.close_all()
        receipt=OUTPUT/'browser.json'
        if receipt.exists():
            body=json.loads(receipt.read_text());body['owned_backend_stopped']=server.poll() is not None
            body['owned_database']=str(owned/'qa.sqlite3');body['exit_code']=code
            receipt.write_text(json.dumps(body,indent=2)+'\n')
    if receipt.exists():
        body=json.loads(receipt.read_text());body['scratch_database_removed']=not (owned/'qa.sqlite3').exists()
        receipt.write_text(json.dumps(body,indent=2)+'\n')
    return code


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--inspect-feedback',action='store_true')
    args=parser.parse_args()
    if args.inspect_feedback:
        inspect_feedback()
    else:
        raise SystemExit(run())
