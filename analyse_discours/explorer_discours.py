"""Explorer les discours : phrases ET statistiques par pays, pour un mot ou un thème.

Version enrichie de chercher_mot.py (qui est conservé tel quel).

Utilisation (depuis n'importe quel dossier) :
    python analyse_discours/explorer_discours.py

- À gauche : choisir un thème, puis un mot (ou taper un autre mot puis Entrée).
  Le bouton "Statistiques du thème entier" calcule les stats sur tous les mots du thème.
- Onglet "Statistiques par pays" : un tableau par pays (cliquer sur un en-tête
  de colonne pour trier) et un bouton pour afficher un graphique.
  Double-cliquer sur un pays affiche ses phrases dans l'onglet "Phrases".
- Onglet "Phrases" : les phrases où le mot apparaît, avec le mot surligné.
"""
import tkinter as tk
import webbrowser
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText

import matplotlib.pyplot as plt

from chercher_mot import charger_discours, chercher, motif_du_mot
from statistiques import preparer_discours, stats_globales, stats_par_pays
from themes import THEMES

# Dans le graphique, on ne montre que les pays avec au moins ce nombre de discours
MIN_DISCOURS_GRAPHIQUE = 3

COLONNES = {
    "pays": "Pays",
    "discours": "Discours dans le pays",
    "discours_avec_mot": "Discours qui en parlent",
    "pct_discours": "% des discours",
    "occurrences": "Occurrences",
    "pour_10000_mots": "Pour 10 000 mots",
}


class Explorateur:
    def __init__(self, racine, discours):
        self.racine = racine
        self.discours = discours
        self.mots_recherches = []   # mot(s) actuellement étudiés
        self.nom_recherche = ""     # texte affiché : "paix" ou "thème migrations"
        self.stats = None           # DataFrame des stats par pays

        racine.title(f"Discours du pape François : explorateur ({len(discours)} discours)")
        racine.geometry("1300x800")

        self.construire_colonne_gauche()
        self.construire_partie_droite()

        self.choix_theme.current(0)
        self.afficher_mots_du_theme()

    # ------------------------------------------------------------------
    # Construction de la fenêtre
    # ------------------------------------------------------------------

    def construire_colonne_gauche(self):
        gauche = ttk.Frame(self.racine, padding=8)
        gauche.pack(side="left", fill="y")

        ttk.Label(gauche, text="Thème :").pack(anchor="w")
        self.choix_theme = ttk.Combobox(gauche, values=list(THEMES), state="readonly", width=38)
        self.choix_theme.pack(anchor="w")
        self.choix_theme.bind("<<ComboboxSelected>>", self.afficher_mots_du_theme)

        ttk.Button(gauche, text="Statistiques du thème entier",
                   command=self.etudier_theme).pack(anchor="w", pady=(4, 10))

        ttk.Label(gauche, text="Mot (occurrences) :").pack(anchor="w")
        self.liste_mots = tk.Listbox(gauche, width=40, height=28, exportselection=False)
        self.liste_mots.pack(anchor="w", fill="y", expand=True)
        self.liste_mots.bind("<<ListboxSelect>>", self.mot_choisi_dans_liste)

        ttk.Label(gauche, text="Autre mot (puis Entrée) :").pack(anchor="w", pady=(8, 0))
        self.case_mot = ttk.Entry(gauche, width=40)
        self.case_mot.pack(anchor="w")
        self.case_mot.bind("<Return>", lambda e: self.etudier([self.case_mot.get().strip()],
                                                              self.case_mot.get().strip()))

    def construire_partie_droite(self):
        droite = ttk.Frame(self.racine, padding=8)
        droite.pack(side="left", fill="both", expand=True)

        self.bilan = ttk.Label(droite, text="Choisissez un mot ou un thème à gauche.",
                               font=("Segoe UI", 11, "bold"))
        self.bilan.pack(anchor="w", pady=(0, 6))

        self.onglets = ttk.Notebook(droite)
        self.onglets.pack(fill="both", expand=True)

        # --- Onglet statistiques ---
        onglet_stats = ttk.Frame(self.onglets, padding=6)
        self.onglets.add(onglet_stats, text="Statistiques par pays")

        haut = ttk.Frame(onglet_stats)
        haut.pack(fill="x")
        self.resume_stats = ttk.Label(haut, text="", justify="left")
        self.resume_stats.pack(side="left", anchor="w")
        ttk.Button(haut, text="Graphique", command=self.afficher_graphique).pack(side="right")

        self.tableau = ttk.Treeview(onglet_stats, columns=list(COLONNES), show="headings")
        for colonne, titre in COLONNES.items():
            self.tableau.heading(colonne, text=titre,
                                 command=lambda c=colonne: self.trier_tableau(c))
            self.tableau.column(colonne, width=170 if colonne == "pays" else 130,
                                anchor="w" if colonne == "pays" else "e")
        self.tableau.pack(fill="both", expand=True, pady=6)
        self.tableau.bind("<Double-1>", self.pays_double_clique)

        ttk.Label(onglet_stats, foreground="#555555", text=(
            "« Pour 10 000 mots » est l'indicateur à comparer entre pays (il tient compte de la "
            "quantité de texte). Attention aux pays avec très peu de discours. "
            "Double-cliquer sur un pays pour lire ses phrases.")).pack(anchor="w")

        # --- Onglet phrases ---
        onglet_phrases = ttk.Frame(self.onglets, padding=6)
        self.onglets.add(onglet_phrases, text="Phrases")

        filtre = ttk.Frame(onglet_phrases)
        filtre.pack(fill="x")
        ttk.Label(filtre, text="Pays :").pack(side="left")
        self.choix_pays = ttk.Combobox(filtre, state="readonly", width=30)
        self.choix_pays.pack(side="left", padx=4)
        self.choix_pays.bind("<<ComboboxSelected>>", lambda e: self.afficher_phrases())

        self.zone_texte = ScrolledText(onglet_phrases, wrap="word", font=("Segoe UI", 10))
        self.zone_texte.pack(fill="both", expand=True, pady=(6, 0))
        self.zone_texte.tag_config("titre", font=("Segoe UI", 11, "bold"), foreground="#1a3d6d")
        self.zone_texte.tag_config("infos", foreground="#555555")
        self.zone_texte.tag_config("lien", foreground="blue", underline=True)
        self.zone_texte.tag_config("surligne", background="yellow", font=("Segoe UI", 10, "bold"))

    # ------------------------------------------------------------------
    # Choix du mot ou du thème
    # ------------------------------------------------------------------

    def afficher_mots_du_theme(self, event=None):
        """Liste les mots du thème choisi, du plus au moins fréquent dans le corpus."""
        total = {}
        for mot in THEMES[self.choix_theme.get()]:
            total[mot] = sum(d["compte_mots"][mot] for d in self.discours)
        self.mots_affiches = sorted(total, key=total.get, reverse=True)
        self.liste_mots.delete(0, "end")
        for mot in self.mots_affiches:
            self.liste_mots.insert("end", f"{mot} ({total[mot]})")

    def mot_choisi_dans_liste(self, event=None):
        selection = self.liste_mots.curselection()
        if selection:
            mot = self.mots_affiches[selection[0]]
            self.etudier([mot], mot)

    def etudier_theme(self):
        theme = self.choix_theme.get()
        self.etudier(THEMES[theme], f"thème « {theme} »")

    def etudier(self, mots, nom):
        """Calcule les stats et les phrases pour une liste de mots."""
        mots = [m for m in mots if m]
        if not mots:
            return
        self.mots_recherches = mots
        self.nom_recherche = nom

        # Statistiques
        globales = stats_globales(mots, self.discours)
        self.stats = stats_par_pays(mots, self.discours)
        self.bilan.config(text=(
            f"{nom} : {globales['occurrences']} occurrences, dans {globales['discours_avec_mot']} "
            f"discours sur {globales['discours']} ({globales['pct_discours']} %)"))
        hors_vatican = self.stats[~self.stats["pays"].isin(["Vatican / Rome", "Avion", "Non déterminé"])]
        hors_vatican = hors_vatican[hors_vatican["discours_avec_mot"] > 0]
        self.resume_stats.config(text=(
            f"Moyenne du corpus : {globales['pour_10000_mots']} pour 10 000 mots.\n"
            f"Évoqué dans {len(hors_vatican)} pays visités (hors Vatican / Rome)."))
        self.remplir_tableau()

        # Phrases : on remet le filtre sur "Tous les pays"
        pays_avec_mot = sorted(self.stats.loc[self.stats["discours_avec_mot"] > 0, "pays"])
        self.choix_pays.config(values=["Tous les pays"] + pays_avec_mot)
        self.choix_pays.current(0)
        self.afficher_phrases()

    # ------------------------------------------------------------------
    # Onglet statistiques
    # ------------------------------------------------------------------

    def remplir_tableau(self):
        self.tableau.delete(*self.tableau.get_children())
        for _, ligne in self.stats.iterrows():
            self.tableau.insert("", "end", values=[ligne[c] for c in COLONNES])

    def trier_tableau(self, colonne):
        """Trie par la colonne cliquée (décroissant, ou alphabétique pour les pays)."""
        if self.stats is not None:
            self.stats = self.stats.sort_values(colonne, ascending=(colonne == "pays"),
                                                ignore_index=True)
            self.remplir_tableau()

    def pays_double_clique(self, event=None):
        selection = self.tableau.selection()
        if selection:
            pays = self.tableau.item(selection[0], "values")[0]
            if pays in self.choix_pays.cget("values"):
                self.choix_pays.set(pays)
                self.afficher_phrases()
                self.onglets.select(1)

    def afficher_graphique(self):
        """Diagramme en barres : fréquence pour 10 000 mots par pays."""
        if self.stats is None:
            return
        donnees = self.stats[self.stats["discours"] >= MIN_DISCOURS_GRAPHIQUE]
        donnees = donnees.sort_values("pour_10000_mots").tail(25)  # 25 pays les plus élevés
        moyenne = stats_globales(self.mots_recherches, self.discours)["pour_10000_mots"]

        plt.figure(figsize=(9, 8))
        plt.barh(donnees["pays"], donnees["pour_10000_mots"], color="#4a7ab5")
        plt.axvline(moyenne, color="red", linestyle="--", label=f"moyenne du corpus ({moyenne})")
        plt.xlabel("Occurrences pour 10 000 mots")
        plt.title(f"{self.nom_recherche} : fréquence par pays\n"
                  f"(pays avec au moins {MIN_DISCOURS_GRAPHIQUE} discours)")
        plt.legend()
        plt.tight_layout()
        plt.show(block=False)

    # ------------------------------------------------------------------
    # Onglet phrases
    # ------------------------------------------------------------------

    def afficher_phrases(self):
        zone = self.zone_texte
        zone.config(state="normal")
        zone.delete("1.0", "end")

        pays_choisi = self.choix_pays.get()
        nb_phrases = 0
        numero = 0
        for mot in self.mots_recherches:
            motif = motif_du_mot(mot)
            for d, phrases in chercher(mot, self.discours):
                if pays_choisi != "Tous les pays" and d["pays"] != pays_choisi:
                    continue
                numero += 1
                nb_phrases += len(phrases)
                zone.insert("end", f"[{mot}]  {d['date']} — {d['titre']}\n", "titre")
                zone.insert("end", f"Pays : {d['pays']}   |   Lieu : {d['lieu']}\n", "infos")
                if d["voyage"]:
                    zone.insert("end", f"Voyage : {d['voyage']}\n", "infos")
                tag_lien = f"lien{numero}"
                zone.insert("end", d["url"] + "\n", ("lien", tag_lien))
                zone.tag_bind(tag_lien, "<Button-1>", lambda e, url=d["url"]: webbrowser.open(url))
                for phrase in phrases:
                    zone.insert("end", "  • ")
                    position = 0
                    for trouve in motif.finditer(phrase):
                        zone.insert("end", phrase[position:trouve.start()])
                        zone.insert("end", trouve.group(), "surligne")
                        position = trouve.end()
                    zone.insert("end", phrase[position:] + "\n")
                zone.insert("end", "\n")

        zone.insert("1.0", f"{nb_phrases} phrases ({pays_choisi})\n\n", "infos")
        zone.config(state="disabled")
        zone.yview_moveto(0)


if __name__ == "__main__":
    print("Chargement des discours...")
    tous_les_discours = preparer_discours(charger_discours())
    print(f"{len(tous_les_discours)} discours chargés")

    fenetre = tk.Tk()
    Explorateur(fenetre, tous_les_discours)
    fenetre.mainloop()
