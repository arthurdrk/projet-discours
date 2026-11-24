"""Statistiques d'un mot ou d'un thème, par pays.

Pour chaque pays, on calcule :
- discours : nombre de discours prononcés dans ce pays
- discours_avec_mot : nombre de ces discours qui contiennent le mot (ou un mot du thème)
- pct_discours : part des discours du pays qui en parlent (en %)
- occurrences : nombre total d'emplois du mot dans les discours du pays
- pour_10000_mots : occurrences pour 10 000 mots prononcés dans ce pays.
  C'est l'indicateur à utiliser pour comparer les pays, car il tient compte
  du fait qu'on a beaucoup plus de texte pour le Vatican que pour l'Albanie.

Utilisation dans un notebook :
    from chercher_mot import charger_discours
    from statistiques import preparer_discours, stats_par_pays
    discours = preparer_discours(charger_discours())
    stats_par_pays(["réfugiés", "migrants"], discours)
"""
from collections import Counter

import pandas as pd

from compter_mots import decouper_en_mots
from pays import pays_du_discours
from villes import ville_du_discours


def preparer_discours(discours):
    """Ajoute à chaque discours son pays, sa ville, le compte de ses mots et sa longueur."""
    for d in discours:
        mots = decouper_en_mots(d["texte"])
        d["pays"] = pays_du_discours(d)
        d["ville"] = ville_du_discours(d)   # None si inconnue (ou dans l'avion)
        d["compte_mots"] = Counter(mots)
        d["nb_mots"] = len(mots)
    return discours


def stats_par_pays(mots, discours):
    """Renvoie un DataFrame (une ligne par pays) pour une liste de mots.

    Pour un seul mot, passer une liste d'un élément : ["paix"].
    Pour un thème, passer la liste de ses mots : THEMES["migrations"].
    """
    mots = [m.lower() for m in mots]
    lignes = []
    for d in discours:
        occurrences = sum(d["compte_mots"][m] for m in mots)
        lignes.append({
            "pays": d["pays"],
            "nb_mots": d["nb_mots"],
            "occurrences": occurrences,
            "contient": occurrences > 0,
        })
    tableau = pd.DataFrame(lignes)

    stats = tableau.groupby("pays").agg(
        discours=("contient", "size"),
        discours_avec_mot=("contient", "sum"),
        occurrences=("occurrences", "sum"),
        nb_mots=("nb_mots", "sum"),
    )
    stats["pct_discours"] = (100 * stats["discours_avec_mot"] / stats["discours"]).round(1)
    stats["pour_10000_mots"] = (10000 * stats["occurrences"] / stats["nb_mots"]).round(2)

    stats = stats.reset_index()
    stats = stats[["pays", "discours", "discours_avec_mot", "pct_discours",
                   "occurrences", "pour_10000_mots"]]
    return stats.sort_values("pour_10000_mots", ascending=False, ignore_index=True)


def stats_globales(mots, discours):
    """Mêmes indicateurs, mais sur l'ensemble du corpus (une seule ligne)."""
    mots = [m.lower() for m in mots]
    nb_discours = len(discours)
    occurrences = sum(d["compte_mots"][m] for d in discours for m in mots)
    avec_mot = sum(any(d["compte_mots"][m] for m in mots) for d in discours)
    nb_mots = sum(d["nb_mots"] for d in discours)
    return {
        "discours": nb_discours,
        "discours_avec_mot": avec_mot,
        "pct_discours": round(100 * avec_mot / nb_discours, 1),
        "occurrences": occurrences,
        "pour_10000_mots": round(10000 * occurrences / nb_mots, 2),
    }
