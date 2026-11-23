"""Tests de la collecte et de la préparation, sans accès au réseau.

Lancer depuis la racine du projet : python -m unittest discover -s tests
"""
import unittest
from datetime import date
from unittest.mock import patch

import pandas as pd
from bs4 import BeautifulSoup

from acquisition import preparer_corpus
from acquisition import telecharger_discours as td

SITE = "https://www.vatican.va/content/francesco/en"


def faux_site(pages):
    """Remplace telecharger() : renvoie la page HTML prévue pour chaque adresse."""
    return lambda url: BeautifulSoup(pages[url], "html.parser")


class Collecte(unittest.TestCase):
    def setUp(self):
        td.discours_du_mois.cache_clear()

    def test_dates_du_voyage(self):
        cas = {
            "Apostolic Journey to Rio de Janeiro, 28th World Youth Day (22-29 July 2013)": ((2013, 7, 22), (2013, 7, 29)),
            "Apostolic Journey ... to Georgia and Azerbaijan (30 September - 2 October 2016)": ((2016, 9, 30), (2016, 10, 2)),
            "Apostolic Journey of Pope Francis to Tirana (Albania) (21 September 2014)": ((2014, 9, 21), (2014, 9, 21)),
            "Apostolic Journey ... to Portugal ... World Youth Day ( 2-6 August 2023)": ((2023, 8, 2), (2023, 8, 6)),
            "Apostolic Journey of the Holy Father to Ajaccio (Sunday, 15 December 2024)": ((2024, 12, 15), (2024, 12, 15)),
            "Apostolic Journey ... to Mozambique, Madagascar and Mauritius (4 -10 September 2019)": ((2019, 9, 4), (2019, 9, 10)),
        }
        for titre, (debut, fin) in cas.items():
            self.assertEqual(td.dates_du_voyage(titre), (date(*debut), date(*fin)), titre)

    def test_lister_voyages_garde_le_titre_et_ecarte_le_voyage_annule(self):
        armenie = "/content/francesco/en/travels/2016/outside/documents/papa-francesco-armenia-2016.html"
        dubai = "/content/francesco/en/travels/2016/outside/documents/dubai-2023.html"
        page = (f'<a href="{armenie}">Apostolic Journey of the Holy Father to Armenia (24-26 June 2016)</a>'
                f'<a href="{armenie}">EN</a><a href="{armenie.replace("/en/", "/fr/")}">FR</a>'
                f'<a href="{dubai}">Apostolic Journey to Dubai (1-3 December 2023)</a>')
        with patch.object(td, "ANNEES", [2016]), \
             patch.object(td, "telecharger", faux_site({f"{SITE}/travels/2016/outside.index.html": page})):
            voyages = td.lister_voyages()
        self.assertEqual(len(voyages), 1)
        voyage = voyages.iloc[0]
        self.assertEqual(voyage["travel_url"], "https://www.vatican.va" + armenie)
        self.assertEqual((voyage["travel_start"], voyage["travel_end"]), (date(2016, 6, 24), date(2016, 6, 26)))

    def test_discours_du_voyage_garde_les_dates_du_voyage_sur_deux_mois(self):
        sept = (f'<a href="{SITE}/speeches/2016/september/documents/papa-francesco_20160929_vatican.html">Vatican</a>'
                f'<a href="{SITE}/speeches/2016/september/documents/papa-francesco_20160930_georgia-autorita.html">Tbilisi</a>'
                f'<a href="https://www.vatican.va/content/francesco/fr/speeches/2016/september/documents/'
                f'papa-francesco_20160930_georgia-autorita.html">FR</a>')
        octo = (f'<a href="{SITE}/speeches/2016/october/documents/20161002-azerbaijan-baku.html">Baku</a>'
                f'<a href="{SITE}/speeches/2016/october/documents/papa-francesco_20161003_rome.html">Rome</a>')
        pages = {f"{SITE}/speeches/2016/september.index.html": sept, f"{SITE}/speeches/2016/october.index.html": octo}
        voyage = {"travel_start": date(2016, 9, 30), "travel_end": date(2016, 10, 2)}
        with patch.object(td, "telecharger", faux_site(pages)):
            discours = td.discours_du_voyage(voyage)
        self.assertEqual(sorted(u.rsplit("/", 1)[-1] for u in discours),
                         ["20161002-azerbaijan-baku.html", "papa-francesco_20160930_georgia-autorita.html"])
        self.assertEqual(discours[f"{SITE}/speeches/2016/october/documents/20161002-azerbaijan-baku.html"], date(2016, 10, 2))


ENTETE = ('<div class="documento"><p align="center">APOSTOLIC JOURNEY TO SRI LANKA AND THE PHILIPPINES<br>'
          '(12-19 JANUARY 2015)</p><p align="center">MEETING WITH FAMILIES</p>'
          '<p align="center">Mall of Asia Arena, Manila<br>Friday, 16 January 2015</p>'
          '<p>Dear Families,</p><p>Thank you.</p><p>© Copyright - Libreria Editrice Vaticana</p></div>')


class Preparation(unittest.TestCase):
    def test_decouper_separe_en_tete_corps_et_lieu(self):
        en_tete, corps, lieu = preparer_corpus.decouper(ENTETE)
        self.assertEqual(lieu, "Mall of Asia Arena, Manila")
        self.assertTrue(en_tete.startswith("APOSTOLIC JOURNEY"))
        self.assertEqual(corps, "Dear Families,\n\nThank you.")

    def test_decouper_lit_une_date_en_italien(self):
        html = ('<div class="documento"><p align="center">MEETING WITH PRIESTS</p>'
                '<p align="center">St Peter’s Parish (Bangkok)<br>Venerdì, 22 novembre 2019</p><p>Dear brothers,</p></div>')
        self.assertEqual(preparer_corpus.decouper(html)[2], "St Peter’s Parish (Bangkok)")

    def test_decouper_sans_en_tete(self):
        self.assertEqual(preparer_corpus.decouper('<div class="documento"><p>Texte seul.</p></div>'), ("", "Texte seul.", ""))

    def test_tri_ecarte_vatican_et_presse(self):
        vatican = ('<div class="documento"><p align="center">ADDRESS TO THE DIPLOMATIC CORPS</p>'
                   '<p align="center">Sala Regia<br>Monday, 12 January 2015</p><p>Excellencies,</p></div>')
        bruts = pd.DataFrame({
            "source_url": [f"{SITE}/speeches/x/documents/{n}.html" for n in ("famille", "vatican", "presse")],
            "title": ["Meeting with families | Francis", "To the Diplomatic Corps | Francis",
                      "In-Flight Press Conference | Francis"],
            "travel_title": ["Sri Lanka"] * 3, "date": ["2015-01-16", "2015-01-12", "2015-01-19"],
            "html": [ENTETE, vatican, ENTETE],
        })
        sorties = {}
        with patch.object(preparer_corpus, "lire", return_value=bruts), \
             patch.object(preparer_corpus, "enregistrer", lambda df, nom: sorties.__setitem__(nom, df)):
            preparer_corpus.main()
        self.assertEqual(list(sorties), ["discours.parquet"])
        self.assertEqual(sorties["discours.parquet"]["event_id"].tolist(), ["famille"])


if __name__ == "__main__":
    unittest.main()
