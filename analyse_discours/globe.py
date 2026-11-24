"""Globe interactif : où le pape François a-t-il prononcé ses discours ?

Ce fichier prépare toutes les données en Python, puis les glisse dans une page
HTML (modele_globe.html) qui affiche un globe plotly qu'on peut faire tourner.

Ce qu'on voit sur la page :
- les pays, colorés au choix selon le nombre de discours, le nombre de voyages
  ou l'indice d'un thème (onglets « Colorer par ») ;
- les villes où il a parlé (carré = Rome, noir = capitale, blanc = autre ville),
  pour voir s'il ne va que dans les capitales ;
- les voyages en avion, tracés Rome -> étapes -> Rome ;
- une fiche à droite quand on clique sur un pays, une ville ou un voyage. Elle dit
  aussi si l'écart d'un thème est vraiment significatif (bootstrap) et quels effets
  résistent à la régression (voir robustesse.py).

Le résultat est une page autonome : analyse_discours/resultats/globe.html
(il faut une connexion internet pour charger plotly et les polices).

Utilisation :
    python analyse_discours/globe.py
ou dans le notebook :
    from globe import creer_globe
    creer_globe(discours)     # discours = preparer_discours(charger_discours())
"""
import datetime
import json
import os
import webbrowser
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go

from compter_mots import DOSSIER_RESULTATS
from robustesse import (PAYS_VERS_REGION, bootstrap_tous_les_themes,
                        regressions_tous_les_themes, tableau_par_discours)
from statistiques import stats_globales, stats_par_pays
from themes import THEMES
from villes import INFOS_VILLES, ROME, bilan_capitales

# ----------------------------------------------------------------------
# Réglages
# ----------------------------------------------------------------------

# Plotly repère les pays par leur code ISO à 3 lettres.
# Si un nouveau pays apparaît dans pays.py, il faut l'ajouter ici.
PAYS_VERS_ISO = {
    "Italie": "ITA", "France": "FRA", "Suisse": "CHE", "Albanie": "ALB",
    "Bosnie-Herzégovine": "BIH", "Turquie": "TUR", "Pologne": "POL", "Suède": "SWE",
    "Portugal": "PRT", "Irlande": "IRL", "Lituanie": "LTU", "Lettonie": "LVA",
    "Estonie": "EST", "Bulgarie": "BGR", "Macédoine du Nord": "MKD", "Roumanie": "ROU",
    "Malte": "MLT", "Chypre": "CYP", "Grèce": "GRC", "Hongrie": "HUN", "Slovaquie": "SVK",
    "Luxembourg": "LUX", "Belgique": "BEL",
    "Jordanie": "JOR", "Palestine": "PSE", "Israël": "ISR", "Égypte": "EGY",
    "Arménie": "ARM", "Géorgie": "GEO", "Azerbaïdjan": "AZE", "Émirats arabes unis": "ARE",
    "Maroc": "MAR", "Irak": "IRQ", "Bahreïn": "BHR", "Kazakhstan": "KAZ",
    "Corée du Sud": "KOR", "Sri Lanka": "LKA", "Philippines": "PHL", "Myanmar": "MMR",
    "Bangladesh": "BGD", "Thaïlande": "THA", "Japon": "JPN", "Mongolie": "MNG",
    "Indonésie": "IDN", "Papouasie-Nouvelle-Guinée": "PNG", "Timor oriental": "TLS",
    "Singapour": "SGP",
    "Kenya": "KEN", "Ouganda": "UGA", "Centrafrique": "CAF", "Mozambique": "MOZ",
    "Madagascar": "MDG", "Maurice": "MUS", "RD Congo": "COD", "Soudan du Sud": "SSD",
    "Brésil": "BRA", "États-Unis": "USA", "Cuba": "CUB", "Mexique": "MEX",
    "Colombie": "COL", "Pérou": "PER", "Chili": "CHL", "Bolivie": "BOL",
    "Paraguay": "PRY", "Équateur": "ECU", "Panama": "PAN", "Canada": "CAN",
}

# Les 6 couleurs de la maquette, du gris (aucun discours) au rouge foncé (beaucoup)
COULEURS = ["#ECEAE4", "#FFE97A", "#FDC23E", "#F68B1F", "#E0401C", "#A3101A"]

# Seuils des classes de discours : 0 | 1-2 | 3-5 | 6-9 | 10-14 | 15 et plus.
# Sans classes, l'Italie (63 discours) écraserait toutes les autres couleurs.
BORNES_DISCOURS = [1, 3, 6, 10, 15]

# Deux discours à l'étranger séparés de plus de 2 jours = deux voyages différents
ECART_MAX_JOURS = 2

MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet",
        "août", "septembre", "octobre", "novembre", "décembre"]

# Conclusions du bootstrap (robustesse.py) -> code court lu par la page
CONCLUSIONS = {"plus que la moyenne": "plus", "moins que la moyenne": "moins",
               "pas d'écart significatif": "ns"}


# ----------------------------------------------------------------------
# Petits outils
# ----------------------------------------------------------------------

def classe(valeur, bornes):
    """Numéro de la classe de couleur (0 à 5) : le nombre de seuils atteints."""
    return sum(valeur >= b for b in bornes)


def echelle_en_paliers(couleurs):
    """Échelle de couleurs plotly « en escalier » : une couleur franche par classe,
    au lieu d'un dégradé continu."""
    n = len(couleurs)
    echelle = []
    for i, couleur in enumerate(couleurs):
        echelle.append([i / n, couleur])         # début de la marche
        echelle.append([(i + 1) / n, couleur])   # fin de la marche
    return echelle


def resume(d):
    """Ce qu'on affiche d'un discours dans les listes de la fiche."""
    return {"date": d["date"], "titre": d["titre"], "url": d["url"],
            "avion": d["pays"] == "Avion"}


def resultats_bootstrap(discours, cle):
    """Intervalles de confiance de robustesse.py, rangés pour être retrouvés vite.

    Renvoie un dictionnaire (thème, pays ou ville) -> {indice, ic_bas, ic_haut, signif},
    où signif vaut "plus" ou "moins" (écart significatif), "ns" (non significatif)
    ou "peu" (moins de 3 discours, pas d'intervalle).
    """
    resultats = {}
    for _, ligne in bootstrap_tous_les_themes(discours, cle=cle).iterrows():
        pas_d_intervalle = pd.isna(ligne["ic_bas"])
        resultats[(ligne["theme"], ligne[cle])] = {
            "indice": ligne["indice"],
            "ic_bas": None if pas_d_intervalle else ligne["ic_bas"],   # None devient null en JSON
            "ic_haut": None if pas_d_intervalle else ligne["ic_haut"],
            "signif": CONCLUSIONS.get(ligne["conclusion"], "peu"),
        }
    return resultats


# ----------------------------------------------------------------------
# Préparer les données de la page
# ----------------------------------------------------------------------

def stats_des_lieux(discours):
    """Tout ce que la fiche d'un pays affiche.

    Renvoie un dictionnaire : pays -> {discours, nb_mots, annees, region, themes, liste}.
    Chaque thème porte son indice et son intervalle de confiance bootstrap.
    """
    # 1. Compter les discours, les mots et les années de chaque pays
    lieux = {}
    for d in discours:
        if d["pays"] not in lieux:
            lieux[d["pays"]] = {"discours": 0, "nb_mots": 0, "annees": set(), "liste": [],
                                "themes": []}
        infos = lieux[d["pays"]]
        infos["discours"] += 1
        infos["nb_mots"] += d["nb_mots"]
        infos["annees"].add(d["date"][:4])
        infos["liste"].append(resume(d))

    for pays, infos in lieux.items():
        infos["annees"] = sorted(infos["annees"])      # un set ne passe pas en JSON
        # la région sert à afficher les résultats de la régression
        infos["region"] = pays if pays == "Italie" else PAYS_VERS_REGION.get(pays)

    # 2. Pour chaque thème : indice du pays et intervalle de confiance
    bootstrap = resultats_bootstrap(discours, "pays")
    sans_intervalle = {"ic_bas": None, "ic_haut": None, "signif": "peu"}
    for theme, mots in THEMES.items():
        moyenne = stats_globales(mots, discours)["pour_10000_mots"]
        for _, ligne in stats_par_pays(mots, discours).iterrows():
            b = bootstrap.get((theme, ligne["pays"]), sans_intervalle)
            lieux[ligne["pays"]]["themes"].append({
                "theme": theme,
                "pour_10000_mots": ligne["pour_10000_mots"],
                "indice": round(ligne["pour_10000_mots"] / moyenne, 2) if moyenne else 0,
                "ic_bas": b["ic_bas"], "ic_haut": b["ic_haut"], "signif": b["signif"],
            })

    # 3. Les thèmes du plus au moins marqué
    for infos in lieux.values():
        infos["themes"].sort(key=lambda t: t["indice"], reverse=True)
    return lieux


def stats_des_villes(discours):
    """Tout ce que la fiche d'une ville affiche.

    Renvoie un dictionnaire : ville -> {pays, capitale, lat, lon, discours, liste, themes},
    où themes contient les 5 thèmes les plus marqués (indice >= 1) avec leur intervalle.
    """
    villes = {}
    for d in discours:
        if d["ville"] is None:      # ville inconnue ou discours dans l'avion
            continue
        if d["ville"] not in villes:
            lat, lon, capitale = INFOS_VILLES[d["ville"]]
            villes[d["ville"]] = {"pays": d["pays"], "capitale": capitale,
                                  "lat": lat, "lon": lon, "discours": 0, "liste": [],
                                  "themes": []}
        villes[d["ville"]]["discours"] += 1
        villes[d["ville"]]["liste"].append(resume(d))

    for (theme, ville), b in resultats_bootstrap(discours, "ville").items():
        if b["indice"] >= 1:
            villes[ville]["themes"].append({"theme": theme, **b})
    for infos in villes.values():
        infos["themes"].sort(key=lambda t: t["indice"], reverse=True)
        infos["themes"] = infos["themes"][:5]
    return villes


def regrouper_voyages(discours):
    """Reconstitue les voyages à partir des dates des discours prononcés à l'étranger.

    On parcourt ces discours dans l'ordre des dates : dès que plus de ECART_MAX_JOURS
    jours séparent deux discours, c'est qu'un nouveau voyage commence. Les conférences
    de presse dans l'avion (pays "Avion") se rangent ainsi d'elles-mêmes dans leur voyage.
    """
    a_l_etranger = [d for d in discours if d["pays"] not in ("Vatican / Rome", "Italie")]
    a_l_etranger.sort(key=lambda d: d["date"])

    # 1. Découper la suite des discours en groupes (un groupe = un voyage)
    groupes = []
    date_precedente = None
    for d in a_l_etranger:
        date = datetime.date.fromisoformat(d["date"])
        if date_precedente is None or (date - date_precedente).days > ECART_MAX_JOURS:
            groupes.append([])
        groupes[-1].append(d)
        date_precedente = date

    # 2. Décrire chaque voyage : pays traversés, villes étapes, discours
    voyages = []
    for groupe in groupes:
        pays, etapes = [], []
        for d in groupe:
            if d["pays"] not in ("Avion", "Non déterminé") and d["pays"] not in pays:
                pays.append(d["pays"])
            if d["ville"] is not None and d["ville"] not in etapes:
                etapes.append(d["ville"])
        if not etapes:      # aucune ville connue : impossible de tracer le voyage
            continue
        debut = groupe[0]["date"]
        voyages.append({
            "nom": f"{', '.join(pays)} ({MOIS[int(debut[5:7]) - 1]} {debut[:4]})",
            "debut": debut,
            "fin": groupe[-1]["date"],
            "pays": pays,
            "etapes": etapes,
            "conferences_avion": sum(d["pays"] == "Avion" for d in groupe),
            "liste": [resume(d) for d in groupe],
        })
    return voyages


# ----------------------------------------------------------------------
# Le globe plotly
# ----------------------------------------------------------------------

def construire_figure(lieux, villes, voyages):
    """Le globe : les pays colorés, puis un trait par voyage, puis les villes.

    L'ordre des traces compte, car la page les retrouve par leur numéro :
    trace 0 = les pays, traces 1 à n = les voyages, dernière trace = les villes.
    """
    figure = go.Figure()

    # 1. Les pays. z est le numéro de classe (0 à 5), pas le nombre brut de discours.
    pays = [p for p in lieux if p in PAYS_VERS_ISO]
    figure.add_trace(go.Choropleth(
        locations=[PAYS_VERS_ISO[p] for p in pays],
        z=[classe(lieux[p]["discours"], BORNES_DISCOURS) for p in pays],
        customdata=[["pays", p] for p in pays],      # pour savoir sur quoi on a cliqué
        text=[f"{p}<br>{lieux[p]['discours']} discours" for p in pays],
        hoverinfo="text",
        zmin=0, zmax=len(COULEURS) - 1,
        colorscale=echelle_en_paliers(COULEURS),
        showscale=False,                             # la légende est dessinée dans la page
        marker_line_color="white", marker_line_width=0.6,
    ))

    # 2. Les voyages : Rome -> étapes -> Rome
    lat_rome, lon_rome, _ = INFOS_VILLES[ROME]
    for i, v in enumerate(voyages):
        lat = [lat_rome] + [villes[e]["lat"] for e in v["etapes"]] + [lat_rome]
        lon = [lon_rome] + [villes[e]["lon"] for e in v["etapes"]] + [lon_rome]
        figure.add_trace(go.Scattergeo(
            lat=lat, lon=lon, mode="lines",
            line=dict(width=1, color="#141414"), opacity=0.45,
            customdata=[["voyage", i]] * len(lat),
            text=[v["nom"]] * len(lat), hoverinfo="text",
            showlegend=False,
        ))

    # 3. Les villes : carré = Rome, noir = capitale, blanc = autre ville
    noms = list(villes)
    figure.add_trace(go.Scattergeo(
        lat=[villes[v]["lat"] for v in noms],
        lon=[villes[v]["lon"] for v in noms],
        customdata=[["ville", v] for v in noms],
        text=[f"{v} ({villes[v]['pays']})<br>{villes[v]['discours']} discours"
              + ("<br>capitale" if villes[v]["capitale"] else "") for v in noms],
        hoverinfo="text",
        mode="markers",
        marker=dict(
            symbol=["square" if v == ROME else "circle" for v in noms],
            # plus il y a de discours, plus le point est gros (plafonné : Rome en a plus de 1 000)
            size=[min(5 + 1.5 * villes[v]["discours"] ** 0.5, 14) for v in noms],
            color=["#141414" if villes[v]["capitale"] else "#ffffff" for v in noms],
            line=dict(color="#141414", width=1.5),
        ),
        showlegend=False,
    ))

    # Le fond de carte : projection « globe », centrée sur Rome
    figure.update_geos(
        projection_type="orthographic",
        projection_rotation=dict(lon=12, lat=30),
        showocean=True, oceancolor="#FFFFFF",
        showland=True, landcolor=COULEURS[0],
        showcountries=True, countrycolor="#FFFFFF", countrywidth=0.6,
        showcoastlines=False, showlakes=False,
        showframe=True, framecolor="#141414", framewidth=1.5,
        bgcolor="rgba(0,0,0,0)",
    )
    figure.update_layout(
        margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor="rgba(0,0,0,0)",
        hoverlabel=dict(bgcolor="#FFFFFF", bordercolor="#141414",
                        font=dict(family="IBM Plex Mono, monospace", size=12, color="#141414")),
    )
    return figure


# ----------------------------------------------------------------------
# Assembler la page
# ----------------------------------------------------------------------

# La page HTML (mise en page, styles et JavaScript) est dans un fichier à part,
# modele_globe.html, pour ne pas noyer le code Python sous 700 lignes de HTML.
# Les mots entre accolades ({figure}, {lieux}...) y sont remplacés par Python.
MODELE_HTML = (Path(__file__).parent / "modele_globe.html").read_text(encoding="utf-8")


def en_json(objet):
    """Transforme un objet Python en texte JSON, lisible directement par le JavaScript."""
    return json.dumps(objet, ensure_ascii=False)


def ouvrir_dans_le_navigateur(chemin):
    """Ouvre la page dans le navigateur par défaut, comme un double-clic sur le fichier.

    Depuis un notebook, webbrowser.open ne fait parfois rien : sous Windows, on passe
    donc d'abord par os.startfile, qui marche à coup sûr.
    """
    try:
        os.startfile(chemin)            # n'existe que sous Windows
    except (AttributeError, OSError):
        webbrowser.open(chemin.resolve().as_uri())


def creer_globe(discours, ouvrir=True):
    """Crée la page du globe, l'ouvre dans le navigateur et renvoie son chemin.

    discours : la liste renvoyée par preparer_discours(charger_discours()).
    ouvrir : False pour créer la page sans l'ouvrir.
    """
    # 1. Les données des fiches
    lieux = stats_des_lieux(discours)
    villes = stats_des_villes(discours)
    voyages = regrouper_voyages(discours)
    bilan = bilan_capitales(discours)

    # 2. Les régressions de robustesse.py : thème -> coefficients des régions et des publics
    coefficients = regressions_tous_les_themes(tableau_par_discours(discours))
    regressions = {theme: groupe.drop(columns="theme").to_dict("records")
                   for theme, groupe in coefficients.groupby("theme")}

    # Un petit bilan dans la console, pour vérifier que tout s'est bien passé
    sans_position = [p for p in lieux if p not in PAYS_VERS_ISO]
    print("Lieux sans couleur sur le globe (montrés par un point ou un bouton) :",
          ", ".join(sans_position))
    print(f"{len(villes)} villes, {len(voyages)} voyages tracés")
    print(f"Hors Rome et Italie : {bilan['pct_en_capitale']} % des discours dans une capitale "
          f"({bilan['capitales']} capitales sur {bilan['villes']} villes)")

    # 3. Le globe, transformé en morceau de HTML
    figure = construire_figure(lieux, villes, voyages)
    html_figure = figure.to_html(
        full_html=False, include_plotlyjs="cdn", div_id="globe",
        config={"displaylogo": False, "scrollZoom": True, "responsive": True,
                "displayModeBar": False},
        default_width="100%", default_height="100%",
    )

    # 4. On remplit le modèle de page
    page = (MODELE_HTML
            .replace("{figure}", html_figure)
            .replace("{lieux}", en_json(lieux))
            .replace("{villes}", en_json(villes))
            .replace("{voyages}", en_json(voyages))
            .replace("{bilan}", en_json(bilan))
            .replace("{regressions}", en_json(regressions))
            .replace("{themes}", en_json(list(THEMES)))
            .replace("{couleurs}", en_json(COULEURS)))

    # 5. On enregistre, et on ouvre si demandé
    DOSSIER_RESULTATS.mkdir(exist_ok=True)
    chemin = DOSSIER_RESULTATS / "globe.html"
    chemin.write_text(page, encoding="utf-8")
    if ouvrir:
        ouvrir_dans_le_navigateur(chemin)
    return chemin


if __name__ == "__main__":
    from chercher_mot import charger_discours
    from statistiques import preparer_discours

    print("Chargement des discours (une à deux minutes)...")
    chemin = creer_globe(preparer_discours(charger_discours()))
    print("Globe enregistré :", chemin)
