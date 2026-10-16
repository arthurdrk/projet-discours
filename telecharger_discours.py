"""Télécharger les discours du Vatican en HTML et TXT."""
import argparse
import hashlib
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE = 'https://www.vatican.va'
DOC = re.compile(r'^/content/([\w-]+)/([a-z-]+)/speeches/(\d{4})(?:/[a-z]+)?/documents/([\w-]+)\.html$')
INDEX = re.compile(r'^/content/([\w-]+)/([a-z-]+)/speeches(?:/\d{4}(?:/[a-z]+)?)?\.index\.html$')


def normalize(url):
    """Garder uniquement les adresses du Vatican, sans paramètres ni ancre."""
    parsed = urlsplit(url)
    if parsed.hostname not in ('www.vatican.va', 'vatican.va', 'w2.vatican.va'):
        raise ValueError('Adresse hors du Vatican : ' + url)
    return urlunsplit(('https', 'www.vatican.va', parsed.path, '', ''))


def fetch(session, url, delay):
    time.sleep(delay)
    response = session.get(url, timeout=60)
    response.raise_for_status()
    normalize(response.url)
    return response.content


def discover(session, start, delay):
    """Parcourir les index descendants, sans suivre les citations des textes."""
    pending, visited, documents, errors = [normalize(start)], set(), set(), []
    while pending:
        url = pending.pop()
        if url in visited:
            continue
        visited.add(url)
        path = urlsplit(url).path
        if DOC.fullmatch(path):
            documents.add(url)
            continue
        if not INDEX.fullmatch(path):
            raise ValueError('Utiliser une URL de discours ou un index .index.html')
        scope = path.removesuffix('.index.html') + '/'
        try:
            soup = BeautifulSoup(fetch(session, url, delay), 'html.parser')
            found = False
            for link in soup.select('a[href]'):
                try:
                    target = normalize(urljoin(url, link['href']))
                except ValueError:
                    continue
                target_path = urlsplit(target).path
                # Même pape, même langue, même période : aucune traduction ajoutée.
                if not target_path.startswith(scope):
                    continue
                if DOC.fullmatch(target_path):
                    documents.add(target)
                    found = True
                elif INDEX.fullmatch(target_path):
                    pending.append(target)
                    found = True
            if not found:
                errors.append({'url': url, 'error': 'Index sans discours ni sous-index : vérifier la page'})
        except requests.RequestException as exc:
            errors.append({'url': url, 'error': str(exc)})
    return sorted(documents), errors


def speech_date(identifier, year):
    for token in re.findall(r'(?<!\d)\d{8}(?!\d)', identifier):
        for pattern in ('%Y%m%d', '%d%m%Y'):
            try:
                date = datetime.strptime(token, pattern).date()
                if str(date.year) == year:
                    return date.isoformat()
            except ValueError:
                pass
    return ''


def collect_one(session, url, root, force=False, delay=1.5):
    pope, language, year, identifier = DOC.fullmatch(urlsplit(url).path).groups()
    date = speech_date(identifier, year)
    suffix = hashlib.sha256(url.encode()).hexdigest()[:10]
    name = f'{date or year + "-date-inconnue"}_{pope}_{language}_{identifier[:100]}_{suffix}'
    folder = root / pope / language / year
    folder.mkdir(parents=True, exist_ok=True)
    html, txt, metadata = [folder / (name + extension) for extension in ('.html', '.txt', '.json')]

    # Réutiliser les fichiers existants seulement si leurs empreintes correspondent.
    if metadata.exists() and not force:
        try:
            old = json.loads(metadata.read_text(encoding='utf-8'))
        except (ValueError, OSError):
            old = {}
        if all(file.exists() and hashlib.sha256(file.read_bytes()).hexdigest() == old.get(key)
               for file, key in [(html, 'html_sha256'), (txt, 'text_sha256')]):
            return old

    raw_html = fetch(session, url, delay)
    soup = BeautifulSoup(raw_html, 'html.parser')
    content = soup.select_one('.documento')
    if content is None:
        raise ValueError('Contenu .documento introuvable')
    for element in content.select('script, style, .translation-field, .container-utility'):
        element.decompose()
    paragraphs = [p.get_text(' ', strip=True) for p in content.select('p') if not p.find('p')]
    text = '\n\n'.join(p for p in paragraphs if p)
    if not text:
        raise ValueError('Texte vide')
    html.write_bytes(raw_html)
    txt.write_text(text + '\n', encoding='utf-8')
    row = {
        'speech_id': identifier, 'event_id': f'{pope}:{identifier}',
        'pope': pope, 'language': language, 'date': date, 'document_type': 'speeches',
        'title': soup.title.get_text(' ', strip=True) if soup.title else identifier,
        'source_url': url, 'html_path': html.relative_to(root).as_posix(),
        'text_path': txt.relative_to(root).as_posix(),
        'html_sha256': hashlib.sha256(raw_html).hexdigest(),
        'text_sha256': hashlib.sha256(txt.read_bytes()).hexdigest(),
        'collected_at': datetime.now(timezone.utc).isoformat(),
    }
    metadata.write_text(json.dumps(row, ensure_ascii=False, indent=2), encoding='utf-8')
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', help='Limiter la collecte à un index ou un discours précis')
    parser.add_argument('--years', nargs='+', type=int, default=list(range(2013, 2026)),
                        help='Années de François à collecter (défaut : 2013 à 2025)')
    parser.add_argument('--output', type=Path, default=Path('corpus_francois'))
    parser.add_argument('--limit', type=int, help='Nombre maximal de textes à télécharger')
    parser.add_argument('--delay', type=float, default=1.5, help='Pause entre les requêtes')
    parser.add_argument('--force', action='store_true', help='Actualiser les fichiers existants')
    parser.add_argument('--discover-only', action='store_true', help='Inventorier sans télécharger les textes')
    args = parser.parse_args()
    if args.delay < 0 or (args.limit is not None and args.limit < 1):
        parser.error('--delay doit être >= 0 et --limit >= 1')
    if any(year < 2013 or year > 2025 for year in args.years):
        parser.error('--years doit contenir des années entre 2013 et 2025')
    args.output.mkdir(parents=True, exist_ok=True)
    starts = [args.url] if args.url else [
        BASE + f'/content/francesco/fr/speeches/{year}.index.html'
        for year in sorted(set(args.years))
    ]
    inventory, errors, report = [], [], []
    successes, interrupted = 0, False

    def save_progress():
        # Un petit état lisible, mis à jour après chaque index et discours.
        for name, data in [('inventaire.json', inventory), ('erreurs.json', errors),
                           ('bilan_collecte.json', report)]:
            target = args.output / name
            temporary = target.with_suffix('.tmp')
            temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
            temporary.replace(target)

    try:
        with requests.Session() as session:
            session.headers['User-Agent'] = 'VaticanSpeechResearch/1.0'
            retry = Retry(total=3, backoff_factor=2, status_forcelist=[429, 500, 502, 503, 504])
            session.mount('https://', HTTPAdapter(max_retries=retry))
            for start in starts:
                print(f'Index : {start}', flush=True)
                row = {'index': start, 'found': 0, 'success': 0, 'status': 'discovering'}
                report.append(row)
                urls, discovery_errors = discover(session, start, args.delay)
                errors.extend(discovery_errors)
                inventory.extend(urls)
                row.update(found=len(urls), status='discovery_error' if discovery_errors else 'inventoried')
                save_progress()
                print(f'{len(urls)} textes trouvés.', flush=True)
                if args.discover_only:
                    continue
                selected = urls if args.limit is None else urls[:max(0, args.limit - successes)]
                row['status'] = 'collecting'
                for i, url in enumerate(selected, 1):
                    print(f'[{i}/{len(selected)}] {url}', flush=True)
                    try:
                        collect_one(session, url, args.output, args.force, args.delay)
                        successes += 1
                        row['success'] += 1
                    except (requests.RequestException, ValueError, OSError) as exc:
                        errors.append({'url': url, 'error': str(exc)})
                        print('Erreur :', exc, flush=True)
                    save_progress()
                row['status'] = ('limited' if len(selected) < len(urls) else
                                 'complete' if not discovery_errors and row['success'] == len(urls) else 'incomplete')
                save_progress()
                if args.limit is not None and successes >= args.limit:
                    break
    except KeyboardInterrupt:
        interrupted = True
        if report:
            report[-1]['status'] = 'interrupted'
        print('\nCollecte interrompue. Relancer la même commande pour reprendre.')
    finally:
        save_progress()
    print(f'{successes} textes disponibles ou téléchargés ; {len(errors)} erreurs.')
    if not args.discover_only:
        print(f'Puis lancer : python preparer_corpus.py --corpus "{args.output}"')
    return 130 if interrupted else 1 if errors else 0


if __name__ == '__main__':
    raise SystemExit(main())
