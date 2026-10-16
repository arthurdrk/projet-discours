"""Lancer JupyterLab avec les dépendances et le noyau locaux du projet."""
import json
import os
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
deps = root / '.deps'
if deps.exists():
    sys.path.insert(0, str(deps))
    os.environ['PYTHONPATH'] = str(deps) + os.pathsep + os.environ.get('PYTHONPATH', '')
runtime = root / '.notebook-runtime'
for name, folder in [('JUPYTER_RUNTIME_DIR', 'connections'), ('IPYTHONDIR', 'ipython'),
                     ('MPLCONFIGDIR', 'matplotlib')]:
    path = runtime / folder
    path.mkdir(parents=True, exist_ok=True)
    os.environ[name] = str(path)
os.environ['JUPYTER_PATH'] = str(runtime) + os.pathsep + str(deps / 'share' / 'jupyter')
kernel = runtime / 'kernels' / 'python3'
kernel.mkdir(parents=True, exist_ok=True)
(kernel / 'kernel.json').write_text(json.dumps({
    'argv': [sys.executable, '-m', 'ipykernel_launcher', '-f', '{connection_file}'],
    'display_name': 'Python — Discours du pape', 'language': 'python',
}), encoding='utf-8')

from jupyterlab.labapp import main

args = [f'--ServerApp.root_dir={root}', '--ServerApp.ip=127.0.0.1',
        '--ServerApp.default_url=/lab/tree/notebooks/01_exploration_corpus.ipynb']
appdir = deps / 'share' / 'jupyter' / 'lab'
if appdir.exists():
    args.append(f'--LabApp.app_dir={appdir}')
main(args + sys.argv[1:])
