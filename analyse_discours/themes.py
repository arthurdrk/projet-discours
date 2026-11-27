"""Listes de mots associées à chaque thème.

Les mots sont écrits en minuscules, avec leurs accents, sous toutes les formes
utiles (singulier, pluriel, féminin), car on compte les mots tels qu'ils
apparaissent dans les discours.

Attention : les mots composés avec un trait d'union ("grands-parents",
"sans-abri") ne peuvent pas être repérés, car la fonction decouper_en_mots
les coupe en deux.

Lancer ce fichier affiche, pour chaque thème, le nombre d'occurrences de
chaque mot dans le corpus, et enregistre analyse_discours/resultats/mots_par_theme.csv :
    python analyse_discours/themes.py
"""
from collections import Counter

import pandas as pd

from compter_mots import DOSSIER_RESULTATS, decouper_en_mots, lire_discours, nettoyer

THEMES = {
    "famille": [
        "famille", "familles", "familial", "familiale", "familiales", "familiaux",
        "mariage", "mariages", "mariés", "époux", "épouse", "épouses",
        "conjugal", "conjugale", "fiancés", "divorcés",
        "parents", "enfant", "enfants", "enfance", "maternité", "paternité",
    ],
    "travail et économie": [
        "travail", "travailleurs", "travailleur", "ouvrier", "ouvriers",
        "emploi", "emplois", "chômage", "chômeurs",
        "économie", "économique", "économiques", "argent", "richesse", "richesses",
        "profit", "profits", "marché", "finance", "financier", "financiers",
        "financière", "financières", "consommation", "consumérisme",
        "entreprise", "entreprises", "entrepreneurs", "salaire", "salaires",
        "banque", "banques", "dette",
    ],
    "paix et guerre": [
        "paix", "pacifique", "guerre", "guerres", "conflit", "conflits",
        "violence", "violences", "violent", "violents", "armes", "armement",
        "terrorisme", "terroristes", "réconciliation", "haine",
        "persécution", "persécutions", "persécutés", "torture", "génocide",
    ],
    "jeunesse et éducation": [
        "jeunes", "jeune", "jeunesse", "éducation", "éducatif", "éducatifs",
        "éducative", "éducatives", "éducateur", "éducateurs",
        "école", "écoles", "scolaire", "université", "universités", "universitaire",
        "étudiant", "étudiants", "élève", "élèves", "enseignants",
        "professeur", "professeurs",
    ],
    "pauvreté et exclusion": [
        "pauvres", "pauvre", "pauvreté", "pauvretés", "misère", "faim",
        "rebut", "déchet", "exclusion", "exclus", "exclu",
        "marginalisés", "marginalisation", "périphérie", "périphéries",
        "démunis", "démunies", "précarité", "inégalité", "inégalités", "indifférence",
    ],
    "dialogue entre religions et entre Églises": [
        "dialogue", "dialoguer", "œcuménique", "œcuméniques", "œcuménisme",
        "orthodoxe", "orthodoxes", "orthodoxie", "patriarche", "patriarches",
        "luthérien", "luthérienne", "luthériens", "anglican", "anglicans",
        "protestant", "protestants", "juif", "juifs", "juive", "juives", "judaïsme",
        "musulman", "musulmans", "islam", "interreligieux", "interreligieuse",
        "religions", "bouddhistes",
    ],
    "dignité et droits humains": [
        "dignité", "droit", "droits", "liberté", "libertés", "justice",
        "injustice", "injustices", "esclavage", "esclaves", "traite",
        "exploitation", "corruption", "discrimination", "discriminations",
        "prostitution", "trafic", "trafiquants",
        # défense de la vie
        "avortement", "euthanasie",
    ],
    "organisation de l'Église et clergé": [
        "prêtre", "prêtres", "évêque", "évêques", "épiscopat", "pasteurs",
        "clergé", "séminaire", "séminaires", "séminariste", "séminaristes",
        "sacerdoce", "sacerdotal", "sacerdotale", "sacerdotales",
        "vocation", "vocations", "diocèse", "diocèses", "paroisse", "paroisses",
        "paroissial", "paroissiale", "curie", "cardinal", "cardinaux",
        "consacrés", "consacrées", "cléricalisme", "carriérisme", "nonce",
    ],
    "miséricorde et pardon": [
        "miséricorde", "miséricordieux", "miséricordieuse", "pardon", "pardonner",
        "pardonne", "tendresse", "compassion", "péché", "péchés", "pécheur",
        "pécheurs", "conversion", "confession", "confesseur", "confesseurs", "repentir",
    ],
    "malades et personnes âgées": [
        "malade", "malades", "maladie", "maladies", "santé", "hôpital", "hôpitaux",
        "soins", "médecin", "médecins", "infirmières", "souffrants",
        "âgée", "âgées", "âgés", "vieillesse", "vieillards", "aînés",
        "handicap", "handicapés",
    ],
    "migrations": [
        "migrant", "migrants", "migration", "migrations", "migratoire", "migratoires",
        "réfugié", "réfugiés", "immigrés", "immigrants", "immigration",
        "émigrés", "émigration", "exil", "exilés", "asile", "déplacés",
        "frontière", "frontières", "étrangers", "xénophobie",
        "lampedusa", "naufrage", "naufrages", "naufragés",
    ],
    "écologie": [
        "création",  # chez François, souvent la création au sens de la nature
        "environnement", "environnemental", "environnementale", "environnementaux",
        "climat", "climatique", "climatiques", "planète", "écologie",
        "écologique", "écologiques", "pollution", "biodiversité", "déforestation",
        "durable", "durables", "laudato",
    ],
}

# Mots volontairement écartés car ambigus (à garder en tête) :
# - "fils", "marie" : surtout le Christ et la Vierge Marie, pas la famille
# - "marche", "marcher" : surtout "marcher ensemble", pas le marché
# - "formation", "enseignement" : souvent la formation des prêtres, l'enseignement de l'Église
# - "terre", "nature" : "Terre sainte", "nature humaine"
# - "religieux", "religieuses" : à la fois les religieux et "liberté religieuse"
# - "accueil", "étranger" : trop généraux ("accueil chaleureux", "à l'étranger")
# - "martyrs" : surtout les saints martyrs, pas la guerre actuelle
# - "soin", "douleur", "souffrance" : souvent au sens spirituel ou général


def compter_mots_des_themes(textes, themes=THEMES):
    """Renvoie un DataFrame (theme, mot, occurrences) pour tous les mots des thèmes."""
    compteur = Counter()
    for texte in textes:
        compteur.update(decouper_en_mots(nettoyer(texte)))

    lignes = []
    for theme, mots in themes.items():
        for mot in mots:
            lignes.append({"theme": theme, "mot": mot, "occurrences": compteur[mot]})
    return pd.DataFrame(lignes)


if __name__ == "__main__":
    textes = lire_discours()
    print(f"{len(textes)} discours lus\n")

    tableau = compter_mots_des_themes(textes)
    for theme, groupe in tableau.groupby("theme", sort=False):
        groupe = groupe.sort_values("occurrences", ascending=False)
        print(f"## {theme} ({groupe['occurrences'].sum()} occurrences)")
        print(", ".join(f"{m} ({o})" for m, o in zip(groupe["mot"], groupe["occurrences"])))
        print()

    DOSSIER_RESULTATS.mkdir(exist_ok=True)
    chemin_csv = DOSSIER_RESULTATS / "mots_par_theme.csv"
    tableau.to_csv(chemin_csv, index=False, encoding="utf-8-sig")
    print(f"Tableau enregistré dans {chemin_csv}")
