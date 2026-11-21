"""Exécuter les notebooks avec le Python courant, sauvegarder leurs sorties et les exporter en HTML.

Usage : python outils/executer_notebooks.py [01 03 ...] [--sans-sauvegarde]
"""
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
from nbconvert import HTMLExporter

filtres = [a for a in sys.argv[1:] if not a.startswith('--')]
sauvegarder = '--sans-sauvegarde' not in sys.argv
sortie_html = ROOT / 'analyses_html'
sortie_html.mkdir(exist_ok=True)
for path in sorted((ROOT / 'notebooks').glob('*.ipynb')):
    if filtres and not any(path.name.startswith(f) for f in filtres):
        continue
    print(f'Exécution : {path.name}', flush=True)
    nb = nbformat.read(path, as_version=4)
    nbformat.validate(nb)
    NotebookClient(nb, timeout=1200, kernel_name='projet-discours',
                   resources={'metadata': {'path': str(path.parent)}}).execute()
    if sauvegarder:
        nbformat.write(nb, path)
        html, _ = HTMLExporter(template_name='lab').from_notebook_node(nb)
        (sortie_html / path.with_suffix('.html').name).write_text(html, encoding='utf-8')
    print(f'OK : {path.name}', flush=True)
