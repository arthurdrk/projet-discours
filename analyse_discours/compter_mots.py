"""Compter combien de fois chaque mot apparaît dans l'ensemble des discours.

Utilisation (depuis n'importe quel dossier) :
    python analyse_discours/compter_mots.py

Résultat : le fichier analyse_discours/resultats/frequences_mots.csv (une ligne par mot).
"""
import re
from collections import Counter
from pathlib import Path

import pandas as pd

# Chemins calculés à partir de l'emplacement de ce fichier
DOSSIER_TRAVAIL = Path(__file__).parent          # analyse_discours/
DOSSIER_PROJET = DOSSIER_TRAVAIL.parent          # projet-discours/
DOSSIER_CORPUS = DOSSIER_PROJET / "corpus_francois"
DOSSIER_RESULTATS = DOSSIER_TRAVAIL / "resultats"


def lire_discours(dossier=DOSSIER_CORPUS):
    """Renvoie la liste des textes de tous les fichiers .txt du dossier."""
    textes = []
    for fichier in sorted(Path(dossier).rglob("*.txt")):
        textes.append(fichier.read_text(encoding="utf-8"))
    return textes


def nettoyer(texte):
    """Retire ce qui n'est pas prononcé par le pape."""
    # Indications entre crochets, par exemple "[Bénédiction]"
    texte = re.sub(r"\[.*?\]", " ", texte)
    # Ligne de copyright à la fin de chaque fichier
    texte = re.sub(r"Copyright ©.*", " ", texte)
    return texte


def decouper_en_mots(texte):
    """Met le texte en minuscules et renvoie la liste de ses mots.

    Les apostrophes séparent les mots : "l'Église" donne "l" et "église".
    """
    texte = texte.lower()
    return re.findall(r"[a-zàâäçéèêëîïôöùûüÿœæ]+", texte)


def compter_mots(textes, longueur_min=4):
    """Compte chaque mot sur l'ensemble des textes.

    Seuls les mots d'au moins `longueur_min` lettres sont gardés
    (4 par défaut, c'est-à-dire plus de 3 lettres).
    Renvoie un DataFrame trié du mot le plus fréquent au moins fréquent.
    """
    compteur = Counter()
    for texte in textes:
        mots = decouper_en_mots(nettoyer(texte))
        mots_gardes = [mot for mot in mots if len(mot) >= longueur_min]
        compteur.update(mots_gardes)

    tableau = pd.DataFrame(compteur.most_common(), columns=["mot", "occurrences"])
    return tableau


if __name__ == "__main__":
    textes = lire_discours()
    print(f"{len(textes)} discours lus")

    frequences = compter_mots(textes)
    print(f"{len(frequences)} mots différents")
    print(frequences.head(30))

    DOSSIER_RESULTATS.mkdir(exist_ok=True)
    chemin_csv = DOSSIER_RESULTATS / "frequences_mots.csv"
    frequences.to_csv(chemin_csv, index=False, encoding="utf-8-sig")
    print(f"Tableau enregistré dans {chemin_csv}")
