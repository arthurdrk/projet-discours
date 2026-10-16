"""Exécuter les notebooks avec le Python courant, puis sauvegarder leurs sorties."""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
runtime = ROOT / '.notebook-runtime'
kernel = runtime / 'kernels' / 'projet-discours'
kernel.mkdir(parents=True, exist_ok=True)
(kernel / 'kernel.json').write_text(json.dumps({
    'argv': [sys.executable, '-m', 'ipykernel_launcher', '-f', '{connection_file}'],
    'display_name': 'Projet discours', 'language': 'python',
}), encoding='utf-8')
os.environ['JUPYTER_PATH'] = str(runtime) + os.pathsep + os.environ.get('JUPYTER_PATH', '')
os.environ['JUPYTER_RUNTIME_DIR'] = str(runtime / 'connections')
os.environ['IPYTHONDIR'] = str(runtime / 'ipython')
os.environ['MPLCONFIGDIR'] = str(runtime / 'matplotlib')

import nbformat
from nbclient import NotebookClient

for path in sorted((ROOT / 'notebooks').glob('*.ipynb')):
    print(f'Exécution : {path.name}', flush=True)
    nb = nbformat.read(path, as_version=4)
    nbformat.validate(nb)
    NotebookClient(nb, timeout=180, kernel_name='projet-discours',
                   resources={'metadata': {'path': str(path.parent)}}).execute()
    nbformat.write(nb, path)
    print(f'OK : {path.name}', flush=True)
