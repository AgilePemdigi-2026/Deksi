"""Run an isolated, explicitly synthetic presentation until stopped."""
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
import dashboard_integration as qa

os.environ['PYTHONDONTWRITEBYTECODE']='1'
os.environ.pop('PYTHONPATH',None)
os.environ.pop('PYTHONHOME',None)
os.environ['DEKSI_PUBLIC_API_TARGET']='http://127.0.0.1:56123'
with tempfile.TemporaryDirectory(dir=qa.SCRATCH,prefix='deksi-b2-presentation-') as temp:
    owned=Path(temp)
    os.environ['DEKSI_TEST_DATABASE']=str(owned/'demo.sqlite3')
    os.environ['DEKSI_TEST_RAW_ROOT']=str(owned/'raw')
    qa.configure()
    from django.core.management import call_command
    call_command('migrate',interactive=False,verbosity=0)
    qa.seed(presentation=True)
    from django.db import connections
    connections.close_all()
    backend=subprocess.Popen([sys.executable,'-B',str(qa.BACKEND/'manage.py'),'runserver','127.0.0.1:56123','--noreload','--settings=backend.test_settings_indicators'],cwd=owned,env=os.environ.copy())
    vite=subprocess.Popen(['node',str(qa.FRONTEND/'node_modules/vite/bin/vite.js'),'--configLoader','runner','--host','127.0.0.1','--port','56122','--strictPort'],cwd=qa.FRONTEND,env=os.environ.copy())
    print('PRESENTATION: http://127.0.0.1:56122/ | DATA UJI SINTETIS, BUKAN RESMI | AUTH BELUM TERKONSOLIDASI',flush=True)
    try:
        while backend.poll() is None and vite.poll() is None:
            time.sleep(1)
        raise RuntimeError('Presentation service exited')
    finally:
        for process in [vite,backend]:
            if process.poll() is None:process.terminate()
        for process in [vite,backend]:
            try:process.wait(timeout=5)
            except subprocess.TimeoutExpired:process.kill();process.wait()
