"""Garder uniquement les noms et les adjectifs prononcés dans les discours.

Chaque mot est analysé DANS SA PHRASE par spaCy (modèle français), qui donne
sa nature grammaticale. Exemple : "être" est un verbe dans "il faut être",
mais un nom dans "un être humain".

Règle utilisée, mot par mot :
1. on compte toutes les natures du mot sur l'ensemble du corpus ;
2. on garde le mot si sa nature la plus fréquente est nom, nom propre ou adjectif ;
3. on retire les mots de la liste MOTS_EXCLUS (adjectifs indéfinis comme "tous") ;
4. "occurrences" = nombre de fois où le mot est employé comme nom ou adjectif.

Utilisation (depuis n'importe quel dossier) :
    python analyse_discours/garder_noms_adjectifs.py

Résultat : analyse_discours/resultats/noms_adjectifs.csv
Installation du modèle (une seule fois) :
    python -m spacy download fr_core_news_md
"""
import re
from collections import Counter, defaultdict

import pandas as pd
import spacy

# On réutilise les fonctions déjà écrites pour lire et nettoyer les discours
from compter_mots import DOSSIER_RESULTATS, lire_discours, nettoyer

# Modèle français de spaCy ("md" est plus précis que "sm")
MODELE = "fr_core_news_md"

# Natures gardées (étiquettes de spaCy) et leur nom en français
NATURES_GARDEES = {
    "NOUN": "nom",
    "PROPN": "nom propre",
    "ADJ": "adjectif",
}

# Adjectifs indéfinis : grammaticalement des adjectifs, mais sans intérêt
# pour repérer des thèmes. Liste modifiable à la main.
MOTS_EXCLUS = {
    "tous", "tout", "toute", "toutes", "autre", "autres", "même", "mêmes",
    "quelques", "certain", "certaine", "certains", "certaines", "plusieurs",
    "chaque", "aucun", "aucune", "telle", "tels", "telles", "divers", "diverses",
}


def est_un_mot(texte, longueur_min=4):
    """Vrai si le texte n'a que des lettres et au moins `longueur_min` lettres."""
    return len(texte) >= longueur_min and re.fullmatch(r"[a-zàâäçéèêëîïôöùûüÿœæ]+", texte)


def compter_noms_adjectifs(textes, longueur_min=4):
    """Renvoie un DataFrame (mot, nature, occurrences) des noms et adjectifs."""
    # On désactive les parties du modèle inutiles ici, pour aller plus vite
    nlp = spacy.load(MODELE, disable=["parser", "ner", "lemmatizer"])
    nlp.max_length = 2_000_000  # certains discours sont longs

    # Pour chaque mot, nombre d'emplois par nature : {"paix": {"NOUN": 480, ...}}
    natures = defaultdict(Counter)

    textes_propres = [nettoyer(texte) for texte in textes]
    for i, doc in enumerate(nlp.pipe(textes_propres, batch_size=20), start=1):
        for token in doc:
            mot = token.text.lower()
            if est_un_mot(mot, longueur_min):
                natures[mot][token.pos_] += 1
        if i % 100 == 0:
            print(f"  {i} discours analysés")

    lignes = []
    for mot, compte in natures.items():
        nature_principale = compte.most_common(1)[0][0]
        if nature_principale in NATURES_GARDEES and mot not in MOTS_EXCLUS:
            # On ne compte que les emplois comme nom, nom propre ou adjectif
            occurrences = sum(compte[pos] for pos in NATURES_GARDEES)
            lignes.append({
                "mot": mot,
                "nature": NATURES_GARDEES[nature_principale],
                "occurrences": occurrences,
            })

    tableau = pd.DataFrame(lignes)
    return tableau.sort_values("occurrences", ascending=False, ignore_index=True)


if __name__ == "__main__":
    textes = lire_discours()
    print(f"{len(textes)} discours lus")

    tableau = compter_noms_adjectifs(textes)
    print(f"{len(tableau)} noms et adjectifs différents")
    print(tableau.head(30))

    DOSSIER_RESULTATS.mkdir(exist_ok=True)
    chemin_csv = DOSSIER_RESULTATS / "noms_adjectifs.csv"
    tableau.to_csv(chemin_csv, index=False, encoding="utf-8-sig")
    print(f"Tableau enregistré dans {chemin_csv}")
