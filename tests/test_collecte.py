import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
from types import SimpleNamespace

from preparer_corpus import extract
from telecharger_discours import collect_one, discover, discover_trip, main, trip_dates
from datetime import date
import json

URL = 'https://www.vatican.va/content/francesco/fr/speeches/2015/september/documents/papa-francesco_20150925_onu-visita.html'
HTML = '''<title>ONU</title><div class="documento"><p align="center">VOYAGE APOSTOLIQUE À CUBA<br>(19-28 septembre 2015)</p><p align="center">DISCOURS</p>
<p align="center">New York<br>Vendredi 25 septembre 2015</p><hr>
<p>La conférence de Paris et la paix.</p></div>'''.encode()


class Tests(unittest.TestCase):
    def test_empty_index_is_reported(self):
        client = SimpleNamespace(get=lambda url, timeout: SimpleNamespace(
            content=b'<html>Page indisponible</html>', url=url, raise_for_status=lambda: None))
        urls, errors = discover(client, 'https://www.vatican.va/content/francesco/fr/speeches/2013.index.html', 0)
        self.assertEqual(urls, [])
        self.assertEqual(len(errors), 1)

    def test_year_follows_months_and_deduplicates_documents(self):
        year = 'https://www.vatican.va/content/francesco/fr/speeches/2015.index.html'
        month = year.replace('2015.index', '2015/september.index')
        pages = {year: f'<a href="{month}">Septembre</a><a href="{URL}">Discours</a>',
                 month: f'<a href="{URL}">Discours</a><a href="{year}">Retour</a>'}
        client = SimpleNamespace(get=lambda url, timeout: SimpleNamespace(
            content=pages[url].encode(), url=url, raise_for_status=lambda: None))
        urls, errors = discover(client, year, 0)
        self.assertEqual(urls, [URL])
        self.assertEqual(errors, [])

    def test_interruption_saves_inventory_and_report(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as tmp:
            with patch('sys.argv', ['collecte', '--perimetre', 'tout', '--langue', 'fr', '--types', 'speeches', '--years', '2015', '--output', tmp]), \
                 patch('telecharger_discours.discover', return_value=([URL], [])), \
                 patch('telecharger_discours.collect_one', side_effect=KeyboardInterrupt):
                self.assertEqual(main(), 130)
            root = Path(tmp)
            self.assertEqual(json.loads((root / 'inventaire.json').read_text()), [URL])
            self.assertEqual(json.loads((root / 'bilan_collecte.json').read_text())[0]['status'], 'interrupted')

    def test_discovery_stays_in_month_and_language(self):
        index = 'https://www.vatican.va/content/francesco/fr/speeches/2015/september.index.html'
        other_language = URL.replace('/fr/', '/en/')
        other_month = URL.replace('/september/', '/october/')
        html = ''.join(f'<a href="{url}">Lien</a>' for url in [URL, other_language, other_month])
        client = SimpleNamespace(get=lambda url, timeout: SimpleNamespace(
            content=html.encode(), url=url, raise_for_status=lambda: None))
        urls, errors = discover(client, index, delay=0)
        self.assertEqual(urls, [URL])
        self.assertEqual(errors, [])

    def test_trip_dates(self):
        self.assertEqual(trip_dates('Journey to Georgia and Azerbaijan (30 September - 2 October 2016)'),
                         (date(2016, 9, 30), date(2016, 10, 2)))
        self.assertEqual(trip_dates('Journey to Mozambique (4 -10 September 2019)'),
                         (date(2019, 9, 4), date(2019, 9, 10)))
        self.assertEqual(trip_dates('Journey to Ajaccio (Sunday, 15 December 2024)'),
                         (date(2024, 12, 15), date(2024, 12, 15)))
        self.assertIsNone(trip_dates('Journey without dates'))

    def test_trip_keeps_speeches_of_trip_dates_in_same_language(self):
        trip = 'https://www.vatican.va/content/francesco/en/travels/2015/outside/documents/papa-francesco-cuba-usa-onu-2015.html'
        month = 'https://www.vatican.va/content/francesco/en/speeches/2015/september.index.html'
        en = 'https://www.vatican.va/content/francesco/en/speeches/2015/september/documents/'
        inside, before = en + 'papa-francesco_20150925_onu-visita.html', en + 'papa-francesco_20150910_rome.html'
        pages = {trip: '<title>Journey to Cuba (19-28 September 2015)</title>'
                       f'<a href="{URL}">fr</a><a href="{inside.replace("/speeches/", "/homilies/")}">homélie</a>',
                 month: f'<a href="{inside}">a</a><a href="{before}">b</a>'}
        client = SimpleNamespace(get=lambda url, timeout: SimpleNamespace(
            content=pages[url].encode(), url=url, raise_for_status=lambda: None))
        urls, errors, title, dates = discover_trip(client, trip, ['speeches'], 0, {})
        self.assertEqual(urls, [inside])
        self.assertEqual(errors, [])
        self.assertEqual(dates, (date(2015, 9, 19), date(2015, 9, 28)))

    def test_english_header_venue(self):
        html = b'''<div class="documento"><p align="center">APOSTOLIC JOURNEY TO SRI LANKA (12-19 JANUARY 2015)</p>
<p align="center">MEETING WITH FAMILIES</p><p align="center">Mall of Asia Arena, Manila<br>Friday, 16 January 2015</p>
<p>Dear Families,</p></div>'''
        row = extract(html, URL.replace('/fr/', '/en/'))
        self.assertEqual(row['venue_raw'], 'Mall of Asia Arena, Manila')
        self.assertEqual(row['text'], 'Dear Families,')

    def test_place_not_mentioned_country(self):
        row = extract(HTML, URL)
        self.assertEqual(row['venue_raw'], 'New York')
        self.assertEqual(row['text'], 'La conférence de Paris et la paix.')

    def test_unknown_place(self):
        row = extract(b'<div class="documento"><p>Paris est cite.</p></div>', URL)
        self.assertEqual(row['venue_status'], 'unknown')
        self.assertEqual(row['text'], 'Paris est cite.')

    def test_resume_checks_html(self):
        class Client:
            calls = 0
            def get(self, url, timeout):
                self.calls += 1
                return SimpleNamespace(content=HTML, url=url, raise_for_status=lambda: None)
        c = Client()
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as tmp:
            root = Path(tmp)
            row = collect_one(c, URL, root, delay=0)
            self.assertTrue((root / row['text_path']).exists())
            collect_one(c, URL, root, delay=0)
            self.assertEqual(c.calls, 1)
            (root / row['html_path']).write_bytes(b'corrupted')
            collect_one(c, URL, root, delay=0)
            self.assertEqual(c.calls, 2)


if __name__ == '__main__':
    unittest.main()
