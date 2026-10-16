#!/usr/bin/env python3
"""Collecte reproductible des discours du Vatican (Python >= 3.10)."""
import argparse
import csv
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
DEFAULT = BASE + '/content/leo-xiv/fr/speeches/2025/december.index.html'
DOC = re.compile(r'^/content/([\w-]+)/([a-z-]+)/speeches/(\d{4})(?:/([a-z]+))?/documents/([\w-]+)\.html$')
INDEX = re.compile(r'^/content/([\w-]+)/([a-z-]+)/speeches(?:/\d{4}(?:/[a-z]+)?)?\.index\.html$')


def normalize(url):
    p = urlsplit(url)
    if p.hostname not in ('www.vatican.va', 'vatican.va', 'w2.vatican.va'):
        raise ValueError('URL hors du domaine Vatican : ' + url)
    return urlunsplit(('https', 'www.vatican.va', p.path, '', ''))


class Collector:
    def __init__(self, delay):
        self.delay = delay
        self.session = requests.Session()
        self.session.headers['User-Agent'] = 'VaticanSpeechResearch/1.0'
        retry = Retry(total=3, backoff_factor=2, status_forcelist=[429, 500, 502, 503, 504])
        self.session.mount('https://', HTTPAdapter(max_retries=retry))
        self.browser = self.pw = None

    def get(self, url):
        time.sleep(self.delay)
        r = self.session.get(url, timeout=(15, 90))
        r.raise_for_status()
        normalize(r.url)
        return r

    def soup(self, url):
        return BeautifulSoup(self.get(url).content, 'html.parser')

    def all_popes(self, root):
        """Suit l’annuaire officiel, les notices, puis leurs sites de pontificat."""
        directory = BASE + '/content/vatican/en/holy-father.html'
        soup = self.soup(directory)
        entries = {}
        for a in soup.select('table a[href]'):
            try:
                url = normalize(urljoin(directory, a['href']))
            except ValueError:
                continue
            entries[url] = a.get_text(' ', strip=True)
        if not entries:
            raise ValueError('Annuaire des papes vide : structure du site à vérifier')
        home_pattern = re.compile(r'^/content/(?!vatican/)([\w-]+)/([a-z-]+)\.html$')
        roots, report, errors = set(), [], []
        for n, (url, name) in enumerate(entries.items(), 1):
            print(f'Pape {n}/{len(entries)} : {name}', flush=True)
            row = {'name': name, 'profile_url': url, 'indexes': [], 'status': ''}
            try:
                profile = self.soup(url)
                homes = {url} if home_pattern.fullmatch(urlsplit(url).path) else set()
                if not homes:
                    # Le site officiel est référencé dans le contenu de la notice.
                    for a in profile.select('a[href]'):
                        try:
                            link = normalize(urljoin(url, a['href']))
                        except ValueError:
                            continue
                        hm = home_pattern.fullmatch(urlsplit(link).path)
                        if hm and ('w2.vatican.va' in a['href'] or a.get_text(strip=True).startswith('http')):
                            homes.add(link)
                for home in homes:
                    hs = profile if home == url else self.soup(home)
                    pope = home_pattern.fullmatch(urlsplit(home).path)[1]
                    for a in hs.select('a[href]'):
                        try:
                            link = normalize(urljoin(home, a['href']))
                        except ValueError:
                            continue
                        im = INDEX.fullmatch(urlsplit(link).path)
                        if im and im[1] == pope:
                            # Un index racine par langue trouvée dans la navigation.
                            roots.add(BASE + f'/content/{pope}/{im[2]}/speeches.index.html')
                            row['indexes'].append(BASE + f'/content/{pope}/{im[2]}/speeches.index.html')
                row['indexes'] = sorted(set(row['indexes']))
                row['status'] = 'indexes_found' if row['indexes'] else 'no_speeches_index_found'
            except Exception as exc:
                row['status'] = 'error'
                row['error'] = str(exc)
                errors.append({'url': url, 'error': str(exc)})
            report.append(row)
            (root / 'papes.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        return sorted(roots), errors

    def discover(self, seeds):
        """Ne suit que les index descendants, jamais les citations des discours."""
        pending, visited, docs, errors = list(seeds), set(), set(), []
        while pending:
            url = normalize(pending.pop(0))
            if url in visited:
                continue
            visited.add(url)
            path = urlsplit(url).path
            if DOC.fullmatch(path):
                docs.add(url)
                continue
            match = INDEX.fullmatch(path)
            if not match:
                raise ValueError('Fournir un index de discours ou un discours : ' + url)
            scope = path.removesuffix('.index.html') + '/'
            try:
                soup = self.soup(url)
                for a in soup.select('a[href]'):
                    try:
                        target = normalize(urljoin(url, a['href']))
                    except ValueError:
                        continue
                    tp = urlsplit(target).path
                    dm = DOC.fullmatch(tp)
                    # Les index français proposent aussi les traductions disponibles.
                    if dm and dm[1] == match[1]:
                        canonical = tp.replace('/' + dm[2] + '/speeches/', '/' + match[2] + '/speeches/', 1)
                        if canonical.startswith(scope):
                            docs.add(target)
                    elif INDEX.fullmatch(tp) and tp.startswith(scope):
                        pending.append(target)
            except Exception as exc:
                errors.append({'url': url, 'error': str(exc)})
        return sorted(docs), errors

    def pdf(self, url, soup, target):
        for a in soup.select('a[href]'):
            link = urljoin(url, a['href'])
            if urlsplit(link).path.lower().endswith('.pdf'):
                try:
                    link = normalize(link)
                except ValueError:
                    continue
                data = self.get(link).content
                if not data.startswith(b'%PDF-'):
                    raise ValueError('Le lien PDF renvoie un autre format')
                target.write_bytes(data)
                return 'direct', link
        if not soup.select_one('#pdfGenerator'):
            raise ValueError('Aucun lien PDF ni bouton #pdfGenerator trouvé')
        if self.browser is None:
            from playwright.sync_api import sync_playwright
            self.pw = sync_playwright().start()
            self.browser = self.pw.chromium.launch()
        page = self.browser.new_page(accept_downloads=True)
        try:
            time.sleep(self.delay)
            page.goto(url, wait_until='load', timeout=90000)
            with page.expect_download(timeout=180000) as event:
                page.locator('#pdfGenerator').click()
            event.value.save_as(str(target))
            if not target.read_bytes().startswith(b'%PDF-'):
                raise ValueError('Le téléchargement obtenu n’est pas un PDF')
            return 'bouton_vatican', ''
        finally:
            page.close()

    def close(self):
        if self.browser:
            self.browser.close()
        if self.pw:
            self.pw.stop()
        self.session.close()


def collect_one(c, url, root, force):
    m = DOC.fullmatch(urlsplit(url).path)
    pope, lang, year, month, identifier = m.groups()
    date = ''
    for token in re.findall(r'(?<!\d)\d{8}(?!\d)', identifier):
        for fmt in ('%Y%m%d', '%d%m%Y'):
            try:
                parsed = datetime.strptime(token, fmt).date()
                if str(parsed.year) == year:
                    date = parsed.isoformat()
                    break
            except ValueError:
                pass
        if date:
            break
    slug = identifier
    # Le suffixe empêche les collisions après une éventuelle troncature du slug.
    suffix = hashlib.sha256(url.encode()).hexdigest()[:10]
    name = f'{date or year + "-date-inconnue"}_{pope}_{lang}_{slug[:100]}_{suffix}'
    folder = root / pope / lang / year
    folder.mkdir(parents=True, exist_ok=True)
    pdf, meta = folder / (name + '.pdf'), folder / (name + '.json')
    if not force and pdf.exists() and meta.exists():
        old = json.loads(meta.read_text(encoding='utf-8'))
        if hashlib.sha256(pdf.read_bytes()).hexdigest() == old.get('sha256'):
            textfile = root / old['text_path']
            if textfile.exists() and hashlib.sha256(textfile.read_bytes()).hexdigest() == old.get('text_sha256'):
                return old
    soup = c.soup(url)
    pdf_soup = BeautifulSoup(str(soup), 'html.parser')
    title = soup.title.get_text(' ', strip=True) if soup.title else identifier
    content = soup.select_one('.documento')
    if content is None:
        raise ValueError('Conteneur du discours introuvable (.documento)')
    for tag in content.select('script, style, .translation-field, .container-utility'):
        tag.decompose()
    paragraphs = [p.get_text(' ', strip=True) for p in content.select('p')]
    text = '\n\n'.join(p for p in paragraphs if p)
    if not text:
        raise ValueError('Texte du discours vide')
    tmp = pdf.with_suffix('.pdf.part')
    try:
        method, pdf_url = c.pdf(url, pdf_soup, tmp)
        tmp.replace(pdf)
    finally:
        tmp.unlink(missing_ok=True)
    txt = folder / (name + '.txt')
    txt.write_text(text + '\n', encoding='utf-8')
    row = dict(speech_id=identifier, pope=pope, language=lang, date=date,
               title=title, source_url=url, pdf_url=pdf_url, pdf_method=method,
               pdf_path=pdf.relative_to(root).as_posix(), text_path=txt.relative_to(root).as_posix(),
               sha256=hashlib.sha256(pdf.read_bytes()).hexdigest(),
               text_sha256=hashlib.sha256(txt.read_bytes()).hexdigest(),
               collected_at=datetime.now(timezone.utc).isoformat())
    meta.write_text(json.dumps(row, ensure_ascii=False, indent=2), encoding='utf-8')
    return row


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--urls', nargs='+', default=[DEFAULT], help='Index mensuel, annuel, général ou discours individuel')
    p.add_argument('--all-popes', action='store_true', help='Découvrir les rubriques Discours depuis l’annuaire officiel des papes')
    p.add_argument('--discover-only', action='store_true', help='Écrire les inventaires sans télécharger les PDF')
    p.add_argument('--output', type=Path, default=Path('donnees_vatican'))
    p.add_argument('--languages', nargs='+', default=['fr'], help='fr en it… ou all ; aucun repli silencieux')
    p.add_argument('--delay', type=float, default=1.5)
    p.add_argument('--limit', type=int, help='Limiter le nombre de documents pour un essai')
    p.add_argument('--force', action='store_true', help='Retélécharger les fichiers déjà présents')
    args = p.parse_args()
    if args.delay < 0 or (args.limit is not None and args.limit < 1):
        p.error('--delay doit être positif ou nul ; --limit doit être >= 1')
    root = args.output.resolve()
    root.mkdir(parents=True, exist_ok=True)
    c = Collector(args.delay)
    rows, errors = [], []
    try:
        seeds = args.urls
        if args.all_popes:
            seeds, errors = c.all_popes(root)
            if not seeds:
                raise ValueError('Aucun index de discours découvert ; consulter papes.json')
        urls, discovery_errors = c.discover(seeds)
        errors.extend(discovery_errors)
        selected = [u for u in urls if 'all' in args.languages or DOC.fullmatch(urlsplit(u).path)[2] in args.languages]
        inventory = [{'url':u, 'language':DOC.fullmatch(urlsplit(u).path)[2], 'selected':u in selected} for u in urls]
        (root / 'inventaire.json').write_text(json.dumps(inventory, indent=2), encoding='utf-8')
        print(f'{len(urls)} versions trouvées ; {len(selected)} retenues selon la langue.')
        if args.discover_only:
            selected = []
        if args.limit:
            selected = selected[:args.limit]
        for i, url in enumerate(selected, 1):
            print(f'[{i}/{len(selected)}] {url}', flush=True)
            try:
                rows.append(collect_one(c, url, root, args.force))
            except Exception as exc:
                errors.append({'url':url, 'error':str(exc)})
                print('ERREUR :', exc, flush=True)
    finally:
        c.close()
        # Index cumulatif : conserve les collectes précédentes du même dossier.
        all_rows = [json.loads(f.read_text(encoding='utf-8')) for f in root.glob('*/*/*/*.json')]
        all_rows.sort(key=lambda r: (r['date'], r['language'], r['speech_id']))
        if all_rows:
            with (root / 'metadata.csv').open('w', encoding='utf-8-sig', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=list(all_rows[0]))
                writer.writeheader()
                writer.writerows(all_rows)
        (root / 'erreurs.json').write_text(json.dumps(errors, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Terminé : {len(rows)} succès, {len(errors)} erreurs. Dossier : {root}')
    return 1 if errors else 0


if __name__ == '__main__':
    raise SystemExit(main())
