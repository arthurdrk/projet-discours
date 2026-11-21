"""Télécharger les textes de François sur vatican.va en HTML et TXT.

Par défaut : les discours en anglais prononcés pendant les voyages apostoliques hors d'Italie.
"""
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
SECTION = r'(?:[a-z_]+(?:-[a-z_]+)*)(?:/[a-z_]+(?:-[a-z_]+)*)?'
DOC = re.compile(r'^/content/([\w-]+)/([a-z-]+)/(' + SECTION + r')(?:/(\d{4})(?:/[a-z]+)?)?/documents/([\w.-]+)\.html$')
INDEX = re.compile(r'^/content/([\w-]+)/([a-z-]+)/' + SECTION + r'(?:/\d{4}(?:/[a-z]+)?)?\.index\.html$')
# Rubriques textuelles du pontificat. Les voyages et événements ne sont que des
# programmes qui renvoient vers ces rubriques.
SECTIONS = ['speeches', 'homilies', 'angelus', 'audiences', 'cotidie', 'messages', 'letters',
            'encyclicals', 'apost_exhortations', 'apost_letters', 'apost_constitutions',
            'bulls', 'motu_proprio', 'prayers']


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


TRIP = re.compile(r'^/content/([\w-]+)/([a-z-]+)/travels/(\d{4})/outside/documents/([\w.-]+)\.html$')


def links(session, url, delay):
    soup = BeautifulSoup(fetch(session, url, delay), 'html.parser')
    found = []
    for link in soup.select('a[href]'):
        try:
            found.append(normalize(urljoin(url, link['href'])))
        except ValueError:
            continue
    return soup, list(dict.fromkeys(found))


def list_trips(session, language, delay):
    """Voyages hors d'Italie : index annuels « outside » puis pages de programme."""
    root = BASE + f'/content/francesco/{language}/travels.index.html'
    _, found = links(session, root, delay)
    years = [u for u in found if re.search(rf'/{language}/travels/\d{{4}}/outside\.index\.html$', u)]
    trips = []
    for year in sorted(years):
        _, found = links(session, year, delay)
        trips += [u for u in found if (m := TRIP.fullmatch(urlsplit(u).path)) and m.group(2) == language]
    return list(dict.fromkeys(trips))


MONTHS = ['january', 'february', 'march', 'april', 'may', 'june', 'july', 'august',
          'september', 'october', 'november', 'december']
# En-tête d'un texte prononcé pendant un voyage (versions anglaise, française, italienne, espagnole).
JOURNEY = re.compile(r'apostolic (?:jo\w*ney|visit)|pilgrimage|visit (?:of|to)|in-flight|papal flight|'
                     r'voyage apostolique|visite apostolique|pèlerinage|viaggio apostolico|pellegrinaggio|'
                     r'viaje apostólico|peregrinación', re.I)


class Excluded(ValueError):
    """Texte téléchargé mais hors du périmètre demandé."""


def trip_dates(title):
    """Dates de début et de fin lues dans « (30 September - 2 October 2016) »."""
    groups = re.findall(r'\(([^()]*\d{4})\s*\)', title)
    if not groups:
        return None
    text = re.sub(r'^[^\d]*,', '', groups[-1]).strip()
    year = int(re.search(r'\d{4}', text).group())
    parts = [part.strip() for part in text.replace(str(year), '').split('-')]

    def parse(part, default_month):
        match = re.fullmatch(r'(\d{1,2})\s*([A-Za-z]*)', part)
        month = match.group(2).lower() or default_month
        return datetime(year, MONTHS.index(month) + 1, int(match.group(1))).date()

    try:
        end = parse(parts[-1], None)
        begin = parse(parts[0], MONTHS[end.month - 1]) if len(parts) > 1 else end
    except (AttributeError, ValueError):
        return None
    return begin, end


def discover_trip(session, trip, sections, delay, month_cache):
    """Textes d'un voyage : liens du programme, puis index mensuels sur les dates du voyage."""
    language = TRIP.fullmatch(urlsplit(trip).path).group(2)
    soup, found = links(session, trip, delay)
    title = re.sub(r'\s+', ' ', soup.title.get_text(' ', strip=True)) if soup.title else trip
    prefixes = tuple(f'/content/francesco/{language}/{section}/' for section in sections)
    urls = {u for u in found if DOC.fullmatch(urlsplit(u).path) and urlsplit(u).path.startswith(prefixes)}
    errors = []
    dates = trip_dates(title)
    if dates is None:
        errors.append({'url': trip, 'error': 'Dates du voyage illisibles dans le titre'})
    else:
        begin, end = dates
        months = sorted({(begin.year, begin.month), (end.year, end.month)})
        for section in sections:
            for year, month in months:
                index = BASE + f'/content/francesco/{language}/{section}/{year}/{MONTHS[month - 1]}.index.html'
                if index not in month_cache:
                    try:
                        month_cache[index] = links(session, index, delay)[1]
                    except requests.RequestException as exc:
                        month_cache[index] = []
                        errors.append({'url': index, 'error': str(exc)})
                for u in month_cache[index]:
                    match = DOC.fullmatch(urlsplit(u).path)
                    if not match or not urlsplit(u).path.startswith(prefixes):
                        continue
                    date = speech_date(match.group(5), match.group(4))
                    if date and begin.isoformat() <= date <= end.isoformat():
                        urls.add(u)
    if not urls and not errors:
        errors.append({'url': trip, 'error': 'Voyage sans texte dans les rubriques demandées'})
    return sorted(urls), errors, title, dates


def speech_date(identifier, year):
    """Date tirée de l'identifiant ; sans année dans l'adresse, accepter le pontificat."""
    for token in re.findall(r'(?<!\d)\d{8}(?!\d)', identifier):
        for pattern in ('%Y%m%d', '%d%m%Y'):
            try:
                date = datetime.strptime(token, pattern).date()
                if str(date.year) == year if year else 2013 <= date.year <= 2025:
                    return date.isoformat()
            except ValueError:
                pass
    return ''


def collect_one(session, url, root, force=False, delay=1.5, extra=None, header_pattern=None):
    pope, language, section, year, identifier = DOC.fullmatch(urlsplit(url).path).groups()
    date = speech_date(identifier, year)
    year = year or date[:4] or 'sans-annee'
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
            if extra and any(old.get(k) != v for k, v in extra.items()):
                old.update(extra)
                metadata.write_text(json.dumps(old, ensure_ascii=False, indent=2), encoding='utf-8')
            return old

    raw_html = fetch(session, url, delay)
    soup = BeautifulSoup(raw_html, 'html.parser')
    content = soup.select_one('.documento')
    if content is None:
        raise ValueError('Contenu .documento introuvable')
    for element in content.select('script, style, .translation-field, .container-utility'):
        element.decompose()
    if header_pattern and not header_pattern.search(content.get_text(' ', strip=True)[:700]):
        raise Excluded("Pas de mention de voyage dans l'en-tête")
    paragraphs =[p.get_text(' ', strip=True) for p in content.select('p') if not p.find('p')]
    text = '\n\n'.join(p for p in paragraphs if p)
    if not text:
        raise ValueError('Texte vide')
    html.write_bytes(raw_html)
    txt.write_text(text + '\n', encoding='utf-8')
    row = {
        'speech_id': identifier, 'event_id': f'{pope}:{identifier}',
        'pope': pope, 'language': language, 'date': date, 'document_type': section,
        'title': soup.title.get_text(' ', strip=True) if soup.title else identifier,
        'source_url': url, 'html_path': html.relative_to(root).as_posix(),
        'text_path': txt.relative_to(root).as_posix(),
        'html_sha256': hashlib.sha256(raw_html).hexdigest(),
        'text_sha256': hashlib.sha256(txt.read_bytes()).hexdigest(),
        'collected_at': datetime.now(timezone.utc).isoformat(),
        **(extra or {}),
    }
    metadata.write_text(json.dumps(row, ensure_ascii=False, indent=2), encoding='utf-8')
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', help='Limiter la collecte à un index ou un discours précis')
    parser.add_argument('--perimetre', choices=['voyages', 'tout'], default='voyages',
                        help="voyages : textes des voyages hors d'Italie (défaut) ; tout : rubriques complètes")
    parser.add_argument('--langue', default='en', help='Langue des textes (défaut : en)')
    parser.add_argument('--types', nargs='+', choices=SECTIONS,
                        help='Rubriques à collecter (défaut : speeches pour les voyages, toutes sinon)')
    parser.add_argument('--years', nargs='+', type=int,
                        help='Années à garder (défaut : tout le pontificat, 2013 à 2025)')
    parser.add_argument('--output', type=Path, help='Dossier de sortie (défaut : corpus_<perimetre>_<langue>)')
    parser.add_argument('--limit', type=int, help='Nombre maximal de textes à télécharger')
    parser.add_argument('--delay', type=float, default=1.5, help='Pause entre les requêtes')
    parser.add_argument('--force', action='store_true', help='Actualiser les fichiers existants')
    parser.add_argument('--discover-only', action='store_true', help='Inventorier sans télécharger les textes')
    args = parser.parse_args()
    if args.delay < 0 or (args.limit is not None and args.limit < 1):
        parser.error('--delay doit être >= 0 et --limit >= 1')
    if args.years and any(year < 2013 or year > 2025 for year in args.years):
        parser.error('--years doit contenir des années entre 2013 et 2025')
    if not re.fullmatch(r'[a-z]{2}(?:-[a-z]+)?', args.langue):
        parser.error('--langue doit être un code comme en, fr, es')
    args.types = list(dict.fromkeys(args.types or (['speeches'] if args.perimetre == 'voyages' else SECTIONS)))
    args.output = args.output or Path(f'corpus_{args.perimetre}_{args.langue}')
    args.output.mkdir(parents=True, exist_ok=True)
    trips = args.perimetre == 'voyages' and not args.url

    def wanted(url):
        if not args.years:
            return True
        _, _, _, year, identifier = DOC.fullmatch(urlsplit(url).path).groups()
        year = year or speech_date(identifier, None)[:4]
        return not year or int(year) in args.years
    inventory, errors, report, excluded, month_cache = [], [], [], [], {}
    successes, interrupted = 0, False

    def save_progress():
        # Un petit état lisible, mis à jour après chaque index et discours.
        for name, data in [('inventaire.json', inventory), ('erreurs.json', errors),
                           ('bilan_collecte.json', report), ('exclus.json', excluded)]:
            target = args.output / name
            temporary = target.with_suffix('.tmp')
            temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
            # Sous Windows, un fichier ouvert dans un éditeur peut refuser le remplacement :
            # on réessaie brièvement, sans interrompre la collecte.
            for attempt in range(5):
                try:
                    temporary.replace(target)
                    break
                except PermissionError:
                    time.sleep(.5 * (attempt + 1))
            else:
                print(f'Attention : {target} verrouillé, état gardé dans {temporary}', flush=True)

    try:
        with requests.Session() as session:
            session.headers['User-Agent'] = 'VaticanSpeechResearch/1.0'
            retry = Retry(total=3, backoff_factor=2, status_forcelist=[429, 500, 502, 503, 504])
            session.mount('https://', HTTPAdapter(max_retries=retry))
            if args.url:
                starts = [args.url]
            elif trips:
                starts = list_trips(session, args.langue, args.delay)
                print(f"{len(starts)} voyages hors d'Italie trouvés.", flush=True)
            else:
                starts = [BASE + f'/content/francesco/{args.langue}/{section}.index.html' for section in args.types]
            for start in starts:
                print(f'Index : {start}', flush=True)
                row = {'index': start, 'found': 0, 'success': 0, 'status': 'discovering'}
                report.append(row)
                extra = None
                if trips:
                    urls, discovery_errors, title, dates = discover_trip(
                        session, start, args.types, args.delay, month_cache)
                    extra = {'travel_url': start, 'travel_title': title,
                             'travel_start': dates[0].isoformat() if dates else '',
                             'travel_end': dates[1].isoformat() if dates else ''}
                    row['travel_title'] = title
                else:
                    urls, discovery_errors = discover(session, start, args.delay)
                urls = [url for url in urls if wanted(url)]
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
                        collect_one(session, url, args.output, args.force, args.delay, extra,
                                    JOURNEY if trips else None)
                        successes += 1
                        row['success'] += 1
                    except Excluded as exc:
                        excluded.append({'url': url, 'voyage': start, 'raison': str(exc)})
                        row['excluded'] = row.get('excluded', 0) + 1
                        print('Exclu :', exc, flush=True)
                    except (requests.RequestException, ValueError, OSError) as exc:
                        errors.append({'url': url, 'error': str(exc)})
                        print('Erreur :', exc, flush=True)
                    save_progress()
                done = row['success'] + row.get('excluded', 0)
                row['status'] = ('limited' if len(selected) < len(urls) else
                                 'complete' if not discovery_errors and done == len(urls) else 'incomplete')
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
