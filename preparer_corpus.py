"""Nettoyer les discours téléchargés et produire la table analysée par les notebooks.

Entrée : discours_bruts.parquet (data/ ou S3), produit par telecharger_discours.py.

1. Découpage. Le texte d'un discours commence par un en-tête : quelques paragraphes
   centrés (voyage, public, lieu, date). On le sépare du corps du discours, et on lit
   le lieu dans l'en-tête (ce qui précède la date), pour attribuer ensuite un pays.
2. Tri. On écarte (le nombre de textes écartés par raison est affiché) :
   - les textes dont l'en-tête ne mentionne pas le voyage : discours prononcés au
     Vatican le matin du départ, qui tombent dans les dates du voyage ;
   - les conférences de presse et échanges avec les journalistes, surtout dans
     l'avion : ils ne sont pas prononcés dans le pays visité, et le texte contient
     les questions des journalistes.

Sortie : discours.parquet, dans data/ et sur le S3.
"""
import re

import pandas as pd
from bs4 import BeautifulSoup

from outils.stockage import enregistrer, lire

# Mois et jours en anglais, et en italien : certains en-têtes du site gardent la date italienne.
MOIS = (r"january|february|march|april|may|june|july|august|september|october|november|december|"
        r"gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre")
DATE = re.compile(rf"\b\d{{1,2}}(?:st|nd|rd|th)?\s+(?:{MOIS})\s+\d{{4}}\b|\b(?:{MOIS})\s+\d{{1,2}},?\s+\d{{4}}\b", re.I)
JOUR = re.compile(r"^(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday|"
                  r"lunedì|martedì|mercoledì|giovedì|venerdì|sabato|domenica)\b", re.I)
# Ligne d'en-tête qui annonce le voyage, sans donner le lieu du discours.
LIGNE_VOYAGE = re.compile(r"apostolic (?:journey|visit)|pilgrimage", re.I)
# Mention du voyage au début du texte (« Apostolic Journey », « JOUNEY » mal orthographié, « Visit to »...).
MENTION_VOYAGE = re.compile(r"apostolic (?:jo\w*ney|visit)|pilgrimage|visit (?:of|to)", re.I)
PRESSE = re.compile(r"flight|press conference|journalists|interview", re.I)


def est_centre(p):
    """Paragraphe centré (attribut align ou style CSS) : c'est ainsi que sont mis en forme les en-têtes."""
    return p.get("align", "").lower() == "center" or bool(re.search(r"text-align\s*:\s*center", p.get("style", ""), re.I))


def lieu_avant_date(p):
    """Lignes d'un paragraphe d'en-tête qui précèdent la date ou le jour : « Nairobi, Kenya »."""
    lignes = [re.sub(r"\s+", " ", ligne).strip() for ligne in p.get_text("\n", strip=True).splitlines()]
    avant = []
    for ligne in lignes:
        if DATE.search(ligne) or JOUR.search(ligne):
            break
        avant.append(ligne)
    lieu = " ".join(avant).strip()
    return lieu if len(lieu) < 200 else ""


def decouper(html):
    """En-tête, corps du texte et lieu d'un discours, à partir du HTML de son bloc de texte."""
    contenu = BeautifulSoup(html, "html.parser")
    for bloc in contenu.select("script, style, .translation-field, .container-utility"):
        bloc.decompose()  # liens vers les traductions, boutons d'impression...
    en_tete, corps, lieu = [], [], ""
    dans_en_tete = True
    for p in contenu.select("p"):
        if p.find("p"):  # paragraphe qui en contient d'autres : on lira ceux de l'intérieur
            continue
        texte = p.get_text(" ", strip=True).replace("\xa0", " ")
        if not texte or re.fullmatch(r"[\s*_\[\]]+", texte):  # vide ou simple séparateur
            continue
        if dans_en_tete and est_centre(p):
            en_tete.append(texte)
            if DATE.search(texte) and not LIGNE_VOYAGE.search(texte):
                lieu = lieu_avant_date(p) or lieu
            continue
        dans_en_tete = False  # le premier paragraphe non centré ouvre le corps du discours
        if not texte.startswith(("Copyright", "©")):
            corps.append(texte)
    return "\n".join(en_tete), "\n\n".join(corps), lieu


def main():
    bruts = lire("discours_bruts.parquet")
    print(f"{len(bruts)} discours bruts.")
    df = bruts.drop(columns="html")
    df["header"], df["text"], df["venue_raw"] = zip(*bruts["html"].map(decouper))
    df["event_id"] = df["source_url"].str.extract(r"([^/]+)\.html$", expand=False)
    df["cleaning_status"] = df["header"].ne("").map({True: "initial_centered_header_removed",
                                                     False: "unsegmented"})

    debut = (df["header"] + " " + df["text"]).str[:700]
    df["raison_exclusion"] = ""
    df.loc[~debut.str.contains(MENTION_VOYAGE), "raison_exclusion"] = "en-tête sans mention du voyage (Vatican)"
    df.loc[df["title"].str.contains(PRESSE), "raison_exclusion"] = "conférence de presse ou journalistes"
    garde = df["raison_exclusion"].eq("")

    print(df.loc[~garde, "raison_exclusion"].value_counts().to_string())
    enregistrer(df.loc[garde].drop(columns="raison_exclusion"), "discours.parquet")


if __name__ == "__main__":
    main()
