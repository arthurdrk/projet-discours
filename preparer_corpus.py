"""Préparation locale, conservatrice et auditable des HTML collectés."""
import argparse
import csv
import json
import re
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup

DATE_FR = re.compile(r'\b\d{1,2}(?:er)?\s+(?:janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+\d{4}\b', re.I)
DAY_FR = re.compile(r'^(?:lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche)\b', re.I)


def extract(html, url):
    soup = BeautifulSoup(html, 'html.parser')
    content = soup.select_one('.documento')
    if content is None:
        raise ValueError('Conteneur .documento absent')
    for node in content.select('script, style, .translation-field, .container-utility'):
        node.decompose()
    paragraphs = [p for p in content.select('p') if not p.find('p')]
    header, body, venue, evidence = [], [], '', ''
    in_header = True
    # Ne coupe que la séquence initiale de paragraphes explicitement centrés.
    # En cas de mise en page inconnue, garde le texte et signale le statut.
    for p in paragraphs:
        text = p.get_text(' ', strip=True).replace('\xa0', ' ')
        if not text or re.fullmatch(r'[\s*_\[\]]+', text):
            continue
        centered = p.get('align', '').lower() == 'center' or bool(re.search(r'text-align\s*:\s*center', p.get('style', ''), re.I))
        if in_header and centered:
            header.append(text)
            if DATE_FR.search(text) and not re.search(r'voyage apostolique', text, re.I):
                lines = [re.sub(r'\s+', ' ', s).strip() for s in p.get_text('\n', strip=True).splitlines()]
                before_date = []
                for line in lines:
                    if DATE_FR.search(line) or DAY_FR.search(line):
                        break
                    before_date.append(line)
                candidate = ' '.join(before_date).strip()
                if candidate and len(candidate) < 200:
                    venue, evidence = candidate, text
            continue
        in_header = False
        if not text.startswith(('Copyright', '©')):
            body.append(text)
    links = sorted({urljoin(url, a['href']) for a in content.select('a[href]') if '/travels/' in a['href']})
    return dict(text='\n\n'.join(body), header='\n'.join(header),
                venue_raw=venue, venue_evidence=evidence,
                venue_status='candidate_to_review' if venue else 'unknown',
                cleaning_status='initial_centered_header_removed' if header else 'unsegmented',
                travel_urls=links)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--corpus', type=Path, default=Path('corpus_francois'))
    args = parser.parse_args()
    rows, errors = [], []
    for path in sorted(args.corpus.glob('*/*/*/*.json')):
        meta = json.loads(path.read_text(encoding='utf-8'))
        try:
            extracted = extract((args.corpus / meta['html_path']).read_bytes(), meta['source_url'])
            rows.append(dict(meta, **extracted))
        except Exception as exc:
            errors.append(dict(metadata_path=str(path), error=str(exc)))
    with (args.corpus / 'corpus_nlp.jsonl').open('w', encoding='utf-8') as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + '\n')
    fields = ['event_id', 'language', 'date', 'title', 'venue_raw', 'venue_status', 'venue_evidence', 'source_url']
    # Export automatique distinct d'une éventuelle table d'annotations manuelles.
    with (args.corpus / 'lieux_candidats.csv').open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)
    report = dict(documents=len(rows), events=len({r['event_id'] for r in rows}),
                  venue_candidates=sum(bool(r['venue_raw']) for r in rows),
                  unknown_venues=sum(not r['venue_raw'] for r in rows),
                  empty_bodies=sum(not r['text'].strip() for r in rows),
                  errors=errors)
    (args.corpus / 'qualite.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False))
    return 1 if errors or report['empty_bodies'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
