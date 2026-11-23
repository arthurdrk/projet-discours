"""Télécharger les discours en anglais du pape François pendant ses voyages hors d'Italie.

Source : https://www.vatican.va. Méthode en deux étapes :

1. Les voyages. La page de chaque année liste les voyages hors d'Italie ; le titre
   d'un voyage contient ses dates, par exemple
   « Apostolic Journey ... to Georgia and Azerbaijan (30 September - 2 October 2016) ».
2. Les discours. L'index mensuel des discours (rubrique « speeches ») liste tous les
   discours du mois, avec leur date dans l'adresse. On garde ceux prononcés entre
   le premier et le dernier jour d'un voyage.
   Les pages des voyages ne suffisent pas : après 2016, elles ne renvoient plus
   directement vers les textes.

Ce script ne fait que collecter. Le tri (discours prononcés au Vatican le jour du
départ, conférences de presse dans l'avion) et le nettoyage des textes sont faits
ensuite par preparer_corpus.py.

Résultat : data/discours_bruts.parquet, une ligne par discours avec le HTML du texte,
copié sur le S3 du SSPCloud. Durée : environ 10 minutes (une pause entre deux pages).
"""
import re
import time
from datetime import date
from functools import lru_cache
from urllib.parse import urljoin

import pandas as pd
import requests
from bs4 import BeautifulSoup

from outils.stockage import enregistrer

SITE = "https://www.vatican.va/content/francesco/en"
ANNEES = range(2013, 2025)  # du premier voyage (2013) au dernier (décembre 2024)
PAUSE = 1  # secondes d'attente avant chaque page, pour ne pas surcharger le site
MOIS = ["january", "february", "march", "april", "may", "june", "july",
        "august", "september", "october", "november", "december"]
# Voyage annoncé puis annulé (maladie du pape) : ses discours ont été lus par un autre.
VOYAGES_ANNULES = ["dubai-2023"]

session = requests.Session()
session.headers["User-Agent"] = "Projet etudiant ENSAE - discours du pape Francois"


def telecharger(url):
    """Télécharger une page et la renvoyer lue par BeautifulSoup (3 essais en cas d'erreur)."""
    for essai in range(3):
        time.sleep(PAUSE)
        try:
            reponse = session.get(url, timeout=30)
            reponse.raise_for_status()
            return BeautifulSoup(reponse.content, "html.parser")
        except requests.RequestException:
            if essai == 2:
                raise
            time.sleep(5)


def dates_du_voyage(titre):
    """Dates de début et de fin lues entre les dernières parenthèses du titre.

    « ... (30 September - 2 October 2016) » -> (date(2016, 9, 30), date(2016, 10, 2))
    « ... (22-29 July 2013) »               -> (date(2013, 7, 22), date(2013, 7, 29))
    """
    texte = re.findall(r"\(([^()]*\d{4})\s*\)", titre)[-1]          # « 30 September - 2 October 2016 »
    annee = int(texte[-4:])
    jours = re.findall(r"(\d{1,2})\s*([A-Za-z]*)", texte[:-4])       # [('30', 'September'), ('2', 'October')]
    (jour_debut, mois_debut), (jour_fin, mois_fin) = jours[0], jours[-1]
    mois_fin = MOIS.index(mois_fin.lower()) + 1
    mois_debut = MOIS.index(mois_debut.lower()) + 1 if mois_debut else mois_fin  # « 22-29 July »
    return date(annee, mois_debut, int(jour_debut)), date(annee, mois_fin, int(jour_fin))


def lister_voyages():
    """Voyages hors d'Italie : une ligne par voyage avec son adresse, son titre et ses dates."""
    voyages = []
    for annee in ANNEES:
        page = telecharger(f"{SITE}/travels/{annee}/outside.index.html")
        for lien in page.select('a[href*="/en/travels/"][href*="/outside/documents/"]'):
            titre = lien.get_text(" ", strip=True)
            if not titre.endswith(")"):  # les autres liens sont les versions « EN », « FR »...
                continue
            debut, fin = dates_du_voyage(titre)
            voyages.append({"travel_url": urljoin(SITE, lien["href"]), "travel_title": titre,
                            "travel_start": debut, "travel_end": fin})
    voyages = pd.DataFrame(voyages).drop_duplicates("travel_url")
    annule = voyages["travel_url"].str.contains("|".join(VOYAGES_ANNULES))
    print(f"{len(voyages)} voyages trouvés, dont {annule.sum()} annulé(s) mis de côté.")
    return voyages[~annule]


@lru_cache(maxsize=None)  # un même mois peut servir à deux voyages : on ne le télécharge qu'une fois
def discours_du_mois(annee, mois):
    """Tous les discours d'un mois : {adresse: date}, la date étant lue dans l'adresse."""
    page = telecharger(f"{SITE}/speeches/{annee}/{MOIS[mois - 1]}.index.html")
    discours = {}
    for lien in page.select('a[href*="/en/speeches/"][href*="/documents/"]'):
        url = urljoin(SITE, lien["href"])
        # papa-francesco_20150113_srilanka-...html ou 20240905-indonesia-...html
        aaaammjj = re.search(r"(\d{4})(\d{2})(\d{2})", url.rsplit("/", 1)[-1])
        if aaaammjj:
            discours[url] = date(*map(int, aaaammjj.groups()))
    return discours


def discours_du_voyage(voyage):
    """Adresses et dates des discours prononcés entre le début et la fin du voyage."""
    debut, fin = voyage["travel_start"], voyage["travel_end"]
    mois = sorted({(debut.year, debut.month), (fin.year, fin.month)})
    return {url: jour for annee, m in mois for url, jour in discours_du_mois(annee, m).items()
            if debut <= jour <= fin}


def lire_discours(url):
    """Titre de la page et HTML du bloc qui contient le texte du discours."""
    page = telecharger(url)
    texte = page.select_one(".documento")
    if texte is None:
        raise ValueError(f"Pas de texte (bloc .documento) dans {url}")
    return page.title.get_text(" ", strip=True), str(texte)


def main():
    lignes = []
    for _, voyage in lister_voyages().iterrows():
        discours = discours_du_voyage(voyage)
        print(f"{voyage['travel_start']} {voyage['travel_title'][:70]}... : {len(discours)} discours")
        for url, jour in sorted(discours.items(), key=lambda x: x[1]):
            try:
                titre, html = lire_discours(url)
            except (requests.RequestException, ValueError) as erreur:  # page absente : on continue
                print(f"  Ignoré : {url} ({erreur})")
                continue
            lignes.append({**voyage.to_dict(), "source_url": url, "date": jour, "title": titre, "html": html})
    bruts = pd.DataFrame(lignes)
    for colonne in ["travel_start", "travel_end", "date"]:  # dates en texte AAAA-MM-JJ
        bruts[colonne] = bruts[colonne].astype(str)
    print(f"{len(bruts)} discours téléchargés.")
    enregistrer(bruts, "discours_bruts.parquet")
    print("Étape suivante : python preparer_corpus.py")


if __name__ == "__main__":
    main()
