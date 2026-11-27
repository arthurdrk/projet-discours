"""Fenêtre de recherche : choisir un mot et voir toutes les phrases où il apparaît.

Utilisation (depuis n'importe quel dossier) :
    python analyse_discours/chercher_mot.py

- À gauche : choisir un thème, puis cliquer sur un mot de la liste
  (ou taper n'importe quel mot dans la case "Autre mot" puis Entrée).
- À droite : pour chaque discours qui contient le mot, sa date, son titre,
  son lieu, le voyage éventuel, le lien vers le site du Vatican (cliquable),
  puis les phrases où le mot apparaît, avec le mot surligné.
"""
import json
import re
import tkinter as tk
import webbrowser
from collections import Counter
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText

from compter_mots import DOSSIER_CORPUS, decouper_en_mots, nettoyer
from themes import THEMES

JOURS = r"(?:lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche)"


# ---------------------------------------------------------------------------
# 1. Lecture des discours (sans fenêtre, utilisable aussi dans un notebook)
# ---------------------------------------------------------------------------

def trouver_lieu(texte):
    """Cherche le lieu dans l'en-tête du discours.

    L'en-tête contient une ligne du type
    "Maison présidentielle (Dhaka) Jeudi 30 novembre 2017" :
    le lieu est ce qui précède le jour de la semaine.
    """
    premieres_lignes = texte.splitlines()[:10]
    for ligne in premieres_lignes:
        resultat = re.search(rf"^(.*?)\s*\b{JOURS}\b,?\s+\d{{1,2}}", ligne, re.IGNORECASE)
        if resultat:
            lieu = resultat.group(1).strip(" -,")
            return lieu if lieu else "non indiqué"
    return "non indiqué"


def trouver_voyage(texte):
    """Renvoie la première ligne si le discours fait partie d'un voyage apostolique
    (à l'étranger) ou d'une visite pastorale (en Italie)."""
    premiere_ligne = texte.splitlines()[0] if texte else ""
    if premiere_ligne.upper().startswith(("VOYAGE APOSTOLIQUE", "VISITE PASTORALE")):
        return premiere_ligne
    return ""


def charger_discours(dossier=DOSSIER_CORPUS):
    """Renvoie une liste de dictionnaires, un par discours, triée par date."""
    discours = []
    for fichier_json in dossier.rglob("*.json"):
        meta = json.loads(fichier_json.read_text(encoding="utf-8"))
        if "text_path" not in meta:  # bilan_collecte.json, erreurs.json, etc.
            continue
        texte = (dossier / meta["text_path"]).read_text(encoding="utf-8")
        discours.append({
            "date": meta["date"],
            "titre": meta["title"],
            "url": meta["source_url"],
            "lieu": trouver_lieu(texte),
            "voyage": trouver_voyage(texte),
            "texte": nettoyer(texte),
        })
    discours.sort(key=lambda d: d["date"])
    return discours


def decouper_en_phrases(texte):
    """Coupe le texte en phrases (après . ! ? … suivis d'un espace)."""
    phrases = []
    for paragraphe in texte.split("\n"):
        for phrase in re.split(r"(?<=[.!?…])\s+", paragraphe):
            if phrase.strip():
                phrases.append(phrase.strip())
    return phrases


def motif_du_mot(mot):
    """Expression régulière qui trouve le mot entier, sans tenir compte des majuscules.

    \\b évite de trouver "paix" dans "apaiser".
    """
    return re.compile(rf"\b{re.escape(mot)}\b", re.IGNORECASE)


def chercher(mot, discours):
    """Renvoie la liste des (discours, phrases contenant le mot)."""
    motif = motif_du_mot(mot)
    resultats = []
    for d in discours:
        if motif.search(d["texte"]):
            phrases = [p for p in decouper_en_phrases(d["texte"]) if motif.search(p)]
            resultats.append((d, phrases))
    return resultats


# ---------------------------------------------------------------------------
# 2. La fenêtre
# ---------------------------------------------------------------------------

class FenetreRecherche:
    def __init__(self, racine, discours):
        self.racine = racine
        self.discours = discours

        # Nombre total d'occurrences de chaque mot, pour l'afficher dans la liste
        self.compteur = Counter()
        for d in discours:
            self.compteur.update(decouper_en_mots(d["texte"]))

        racine.title(f"Recherche dans les discours du pape François ({len(discours)} discours)")
        racine.geometry("1200x750")

        # --- Colonne de gauche : choix du mot ---
        gauche = ttk.Frame(racine, padding=8)
        gauche.pack(side="left", fill="y")

        ttk.Label(gauche, text="Thème :").pack(anchor="w")
        self.choix_theme = ttk.Combobox(gauche, values=list(THEMES), state="readonly", width=38)
        self.choix_theme.pack(anchor="w", pady=(0, 8))
        self.choix_theme.bind("<<ComboboxSelected>>", self.afficher_mots_du_theme)

        ttk.Label(gauche, text="Mot (occurrences) :").pack(anchor="w")
        self.liste_mots = tk.Listbox(gauche, width=40, height=30, exportselection=False)
        self.liste_mots.pack(anchor="w", fill="y", expand=True)
        self.liste_mots.bind("<<ListboxSelect>>", self.mot_choisi_dans_liste)

        ttk.Label(gauche, text="Autre mot (puis Entrée) :").pack(anchor="w", pady=(8, 0))
        self.case_mot = ttk.Entry(gauche, width=40)
        self.case_mot.pack(anchor="w")
        self.case_mot.bind("<Return>", lambda event: self.lancer_recherche(self.case_mot.get()))

        # --- Partie de droite : résultats ---
        droite = ttk.Frame(racine, padding=8)
        droite.pack(side="left", fill="both", expand=True)

        self.bilan = ttk.Label(droite, text="Choisissez un mot à gauche.", font=("Segoe UI", 11, "bold"))
        self.bilan.pack(anchor="w")

        self.zone_texte = ScrolledText(droite, wrap="word", font=("Segoe UI", 10))
        self.zone_texte.pack(fill="both", expand=True)

        # Styles utilisés dans la zone de texte
        self.zone_texte.tag_config("titre", font=("Segoe UI", 11, "bold"), foreground="#1a3d6d")
        self.zone_texte.tag_config("infos", foreground="#555555")
        self.zone_texte.tag_config("lien", foreground="blue", underline=True)
        self.zone_texte.tag_config("surligne", background="yellow", font=("Segoe UI", 10, "bold"))
        self.zone_texte.tag_bind("lien", "<Enter>", lambda e: self.zone_texte.config(cursor="hand2"))
        self.zone_texte.tag_bind("lien", "<Leave>", lambda e: self.zone_texte.config(cursor=""))

        # On affiche le premier thème au démarrage
        self.choix_theme.current(0)
        self.afficher_mots_du_theme()

    def afficher_mots_du_theme(self, event=None):
        """Remplit la liste avec les mots du thème choisi, du plus au moins fréquent."""
        mots = THEMES[self.choix_theme.get()]
        mots = sorted(mots, key=lambda m: self.compteur[m], reverse=True)
        self.liste_mots.delete(0, "end")
        self.mots_affiches = mots
        for mot in mots:
            self.liste_mots.insert("end", f"{mot} ({self.compteur[mot]})")

    def mot_choisi_dans_liste(self, event=None):
        selection = self.liste_mots.curselection()
        if selection:
            self.lancer_recherche(self.mots_affiches[selection[0]])

    def lancer_recherche(self, mot):
        mot = mot.strip()
        if not mot:
            return
        resultats = chercher(mot, self.discours)
        nb_phrases = sum(len(phrases) for _, phrases in resultats)
        self.bilan.config(text=f"« {mot} » : {nb_phrases} phrases dans {len(resultats)} discours")

        zone = self.zone_texte
        zone.config(state="normal")
        zone.delete("1.0", "end")
        motif = motif_du_mot(mot)

        for numero, (d, phrases) in enumerate(resultats):
            zone.insert("end", f"{d['date']} — {d['titre']}\n", "titre")
            zone.insert("end", f"Lieu : {d['lieu']}\n", "infos")
            if d["voyage"]:
                zone.insert("end", f"Voyage : {d['voyage']}\n", "infos")
            # Lien cliquable : chaque lien a son propre tag pour connaître son adresse
            tag_lien = f"lien{numero}"
            zone.insert("end", d["url"] + "\n", ("lien", tag_lien))
            zone.tag_bind(tag_lien, "<Button-1>", lambda e, url=d["url"]: webbrowser.open(url))

            for phrase in phrases:
                zone.insert("end", "  • ")
                # On écrit la phrase morceau par morceau pour surligner le mot
                position = 0
                for trouve in motif.finditer(phrase):
                    zone.insert("end", phrase[position:trouve.start()])
                    zone.insert("end", trouve.group(), "surligne")
                    position = trouve.end()
                zone.insert("end", phrase[position:] + "\n")
            zone.insert("end", "\n")

        zone.config(state="disabled")  # lecture seule
        zone.yview_moveto(0)


if __name__ == "__main__":
    print("Chargement des discours...")
    tous_les_discours = charger_discours()
    print(f"{len(tous_les_discours)} discours chargés")

    fenetre = tk.Tk()
    FenetreRecherche(fenetre, tous_les_discours)
    fenetre.mainloop()
