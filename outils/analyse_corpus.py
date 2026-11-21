"""Fonctions communes aux notebooks : discours en anglais des voyages apostoliques de François.

Chargement, pays et continent de chaque discours, type de public, pays mentionnés,
lexiques thématiques, références, palette et style des graphiques.
"""
import os
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = next((p for p in [Path.cwd(), *Path.cwd().parents] if (p / "telecharger_discours.py").exists()),
            Path(__file__).resolve().parents[1])
# La variable CORPUS_FRANCOIS permet de pointer vers un autre corpus préparé (tests).
CORPUS = Path(os.environ.get("CORPUS_FRANCOIS", ROOT / "corpus_voyages_en" / "corpus_nlp.jsonl"))
RESULTATS = ROOT / "resultats"

# ---------------------------------------------------------------------------
# Palette validée (instance de référence du skill dataviz), surfaces et encres.
# ---------------------------------------------------------------------------
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
SURFACE, ENCRE, ENCRE_2, MUET, GRILLE, AXE = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
BLEUS = ["#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec", "#5598e7", "#3987e5",
         "#2a78d6", "#256abf", "#1c5cab", "#184f95", "#104281", "#0d366b"]
GRIS = "#c3c2b7"
ORDRE_CONTINENTS = ["Europe", "Asie", "Afrique", "Amériques", "Moyen-Orient", "Océanie"]
COULEUR_CONTINENT = dict(zip(ORDRE_CONTINENTS, SERIES))


def style():
    """Style matplotlib sobre : marques fines, grille discrète, encre neutre."""
    import matplotlib as mpl
    from matplotlib.colors import LinearSegmentedColormap
    mpl.rcParams.update({
        "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
        "figure.figsize": (11, 5), "figure.dpi": 110, "font.size": 10.5,
        "font.family": ["Segoe UI", "DejaVu Sans", "sans-serif"],
        "axes.edgecolor": AXE, "axes.labelcolor": ENCRE_2, "axes.titlecolor": ENCRE,
        "axes.titlesize": 13, "axes.titleweight": "semibold", "axes.titlelocation": "left",
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "grid.color": GRILLE, "grid.linewidth": .7, "axes.axisbelow": True,
        "xtick.color": MUET, "ytick.color": MUET, "xtick.labelcolor": ENCRE_2, "ytick.labelcolor": ENCRE_2,
        "lines.linewidth": 2, "legend.frameon": False, "legend.labelcolor": ENCRE_2,
        "axes.prop_cycle": mpl.cycler(color=SERIES),
    })
    cmap = LinearSegmentedColormap.from_list("bleus", BLEUS)
    if "bleus" not in mpl.colormaps:
        mpl.colormaps.register(cmap, name="bleus")
    return cmap


def plotly_pret():
    """Afficher Plotly dans JupyterLab et dans l'export HTML."""
    import plotly.io as pio
    pio.renderers.default = "plotly_mimetype+notebook_connected"
    pio.templates.default = "simple_white"


def tuiles(elements):
    """Chiffres clés en tuiles HTML (le chiffre est le graphique)."""
    from IPython.display import HTML, display
    cases = "".join(
        f"<div style='padding:12px 18px;background:{SURFACE};border:1px solid {GRILLE};border-radius:8px;"
        f"min-width:150px'><div style='color:{ENCRE_2};font-size:12px'>{nom}</div>"
        f"<div style='font-size:26px;font-weight:600;color:{ENCRE}'>{valeur}</div></div>"
        for nom, valeur in elements)
    display(HTML(f"<div style='display:flex;gap:12px;flex-wrap:wrap;margin:8px 0'>{cases}</div>"))


def nombre(n):
    return f"{n:,.0f}".replace(",", " ")


def etiquette_directe(ax, x, y, texte, couleur=ENCRE_2, **kw):
    ax.annotate(texte, (x, y), xytext=(4, 0), textcoords="offset points", va="center",
                color=couleur, fontsize=9.5, **kw)


def carte_chaleur(ax, tableau, cmap, fmt="{:.0f}", seuil=.6, couleurs=None, **kw):
    """Matrice annotée : texte blanc sur les cases foncées. `couleurs` peut différer des valeurs affichées."""
    couleurs = tableau if couleurs is None else couleurs
    im = ax.imshow(couleurs.astype(float), cmap=cmap, aspect="auto", **kw)
    haut = np.nanmax(couleurs.to_numpy(dtype=float))
    for i in range(tableau.shape[0]):
        for j in range(tableau.shape[1]):
            v = tableau.iat[i, j]
            if pd.notna(v):
                ax.text(j, i, fmt.format(v), ha="center", va="center", fontsize=8.5,
                        color="white" if couleurs.iat[i, j] > haut * seuil else ENCRE)
    ax.set_xticks(range(tableau.shape[1]), tableau.columns)
    ax.set_yticks(range(tableau.shape[0]), tableau.index)
    ax.grid(False)
    ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    return im


# ---------------------------------------------------------------------------
# Pays (noms anglais) -> ISO3, nom français et continent.
# Recherche sensible à la casse dans les textes (« Turkey » mais pas « turkey »).
# Limites connues : « Congo » seul est attribué à la RD Congo ; « Georgia » peut
# désigner l'État américain ; « Jordan » le fleuve ; « America » les États-Unis.
# ---------------------------------------------------------------------------
PAYS = {
    # ISO3: (nom français, motif anglais, continent)
    "AFG": ("Afghanistan", r"Afghanistan", "Asie"), "ALB": ("Albanie", r"Albania", "Europe"),
    "DZA": ("Algérie", r"Algeria", "Afrique"), "AGO": ("Angola", r"Angola", "Afrique"),
    "ARG": ("Argentine", r"Argentina", "Amériques"), "ARM": ("Arménie", r"Armenia", "Moyen-Orient"),
    "AUS": ("Australie", r"Australia", "Océanie"), "AUT": ("Autriche", r"Austria", "Europe"),
    "AZE": ("Azerbaïdjan", r"Azerbaijan", "Moyen-Orient"), "BHR": ("Bahreïn", r"Bahrai?n|Bahrein", "Moyen-Orient"),
    "BGD": ("Bangladesh", r"Bangladesh", "Asie"), "BEL": ("Belgique", r"Belgium", "Europe"),
    "BEN": ("Bénin", r"Benin", "Afrique"), "BLR": ("Biélorussie", r"Belarus", "Europe"),
    "BOL": ("Bolivie", r"Bolivia", "Amériques"), "BIH": ("Bosnie-Herzégovine", r"Bosnia", "Europe"),
    "BRA": ("Brésil", r"Brazil", "Amériques"), "BGR": ("Bulgarie", r"Bulgaria", "Europe"),
    "BFA": ("Burkina Faso", r"Burkina Faso", "Afrique"), "BDI": ("Burundi", r"Burundi", "Afrique"),
    "KHM": ("Cambodge", r"Cambodia", "Asie"), "CMR": ("Cameroun", r"Cameroon", "Afrique"),
    "CAN": ("Canada", r"Canada", "Amériques"), "CAF": ("Centrafrique", r"Central African Republic", "Afrique"),
    "TCD": ("Tchad", r"Chad", "Afrique"), "CHL": ("Chili", r"Chile", "Amériques"),
    "CHN": ("Chine", r"China", "Asie"), "COL": ("Colombie", r"Colombia", "Amériques"),
    "COG": ("Congo-Brazzaville", r"Republic of the Congo|Congo-Brazzaville", "Afrique"),
    "COD": ("RD Congo", r"Democratic Republic of (?:the )?Congo|DRC|(?<!Republic of the )Congo(?!-Brazzaville)", "Afrique"),
    "CRI": ("Costa Rica", r"Costa Rica", "Amériques"), "CIV": ("Côte d'Ivoire", r"Côte d[’']Ivoire|Ivory Coast", "Afrique"),
    "HRV": ("Croatie", r"Croatia", "Europe"), "CUB": ("Cuba", r"Cuba", "Amériques"),
    "CYP": ("Chypre", r"Cyprus", "Europe"), "CZE": ("Tchéquie", r"Czech Republic|Czechia", "Europe"),
    "DNK": ("Danemark", r"Denmark", "Europe"), "DOM": ("Rép. dominicaine", r"Dominican Republic", "Amériques"),
    "ECU": ("Équateur", r"Ecuador", "Amériques"), "EGY": ("Égypte", r"Egypt", "Moyen-Orient"),
    "SLV": ("Salvador", r"El Salvador", "Amériques"), "ERI": ("Érythrée", r"Eritrea", "Afrique"),
    "EST": ("Estonie", r"Estonia", "Europe"), "ETH": ("Éthiopie", r"Ethiopia", "Afrique"),
    "FIN": ("Finlande", r"Finland", "Europe"), "FRA": ("France", r"France", "Europe"),
    "GAB": ("Gabon", r"Gabon", "Afrique"), "GEO": ("Géorgie", r"Georgia", "Moyen-Orient"),
    "DEU": ("Allemagne", r"Germany", "Europe"), "GHA": ("Ghana", r"Ghana", "Afrique"),
    "GRC": ("Grèce", r"Greece", "Europe"), "GTM": ("Guatemala", r"Guatemala", "Amériques"),
    "HTI": ("Haïti", r"Haiti", "Amériques"), "HND": ("Honduras", r"Honduras", "Amériques"),
    "HUN": ("Hongrie", r"Hungary", "Europe"), "ISL": ("Islande", r"Iceland", "Europe"),
    "IND": ("Inde", r"India", "Asie"), "IDN": ("Indonésie", r"Indonesia", "Asie"),
    "IRN": ("Iran", r"Iran", "Moyen-Orient"), "IRQ": ("Irak", r"Iraq", "Moyen-Orient"),
    "IRL": ("Irlande", r"(?<!Northern )Ireland", "Europe"), "ISR": ("Israël", r"Israel", "Moyen-Orient"),
    "ITA": ("Italie", r"Italy", "Europe"), "JAM": ("Jamaïque", r"Jamaica", "Amériques"),
    "JPN": ("Japon", r"Japan", "Asie"), "JOR": ("Jordanie", r"Jordan", "Moyen-Orient"),
    "KAZ": ("Kazakhstan", r"Kazakhstan", "Asie"), "KEN": ("Kenya", r"Kenya", "Afrique"),
    "KOR": ("Corée du Sud", r"Republic of Korea|South Korea|(?<!North )Korea", "Asie"),
    "PRK": ("Corée du Nord", r"North Korea", "Asie"), "KWT": ("Koweït", r"Kuwait", "Moyen-Orient"),
    "LAO": ("Laos", r"Laos", "Asie"), "LVA": ("Lettonie", r"Latvia", "Europe"),
    "LBN": ("Liban", r"Lebanon", "Moyen-Orient"), "LBR": ("Libéria", r"Liberia", "Afrique"),
    "LBY": ("Libye", r"Libya", "Afrique"), "LTU": ("Lituanie", r"Lithuania", "Europe"),
    "LUX": ("Luxembourg", r"Luxembourg", "Europe"), "MDG": ("Madagascar", r"Madagascar", "Afrique"),
    "MWI": ("Malawi", r"Malawi", "Afrique"), "MYS": ("Malaisie", r"Malaysia", "Asie"),
    "MLI": ("Mali", r"Mali", "Afrique"), "MLT": ("Malte", r"Malta", "Europe"),
    "MUS": ("Maurice", r"Mauritius", "Afrique"), "MEX": ("Mexique", r"Mexico", "Amériques"),
    "MDA": ("Moldavie", r"Moldova", "Europe"), "MNG": ("Mongolie", r"Mongolia", "Asie"),
    "MNE": ("Monténégro", r"Montenegro", "Europe"), "MAR": ("Maroc", r"Morocco", "Afrique"),
    "MOZ": ("Mozambique", r"Mozambique", "Afrique"), "MMR": ("Myanmar", r"Myanmar|Burma", "Asie"),
    "NAM": ("Namibie", r"Namibia", "Afrique"), "NPL": ("Népal", r"Nepal", "Asie"),
    "NLD": ("Pays-Bas", r"Netherlands|Holland", "Europe"), "NZL": ("Nouvelle-Zélande", r"New Zealand", "Océanie"),
    "NIC": ("Nicaragua", r"Nicaragua", "Amériques"), "NER": ("Niger", r"Niger", "Afrique"),
    "NGA": ("Nigeria", r"Nigeria", "Afrique"), "MKD": ("Macédoine du Nord", r"North Macedonia|Macedonia", "Europe"),
    "NOR": ("Norvège", r"Norway", "Europe"), "OMN": ("Oman", r"Oman", "Moyen-Orient"),
    "PAK": ("Pakistan", r"Pakistan", "Asie"), "PSE": ("Palestine", r"Palestine", "Moyen-Orient"),
    "PAN": ("Panama", r"Panama", "Amériques"), "PNG": ("Papouasie-Nouvelle-Guinée", r"Papua New Guinea", "Océanie"),
    "PRY": ("Paraguay", r"Paraguay", "Amériques"), "PER": ("Pérou", r"Peru", "Amériques"),
    "PHL": ("Philippines", r"Philippines", "Asie"), "POL": ("Pologne", r"Poland", "Europe"),
    "PRT": ("Portugal", r"Portugal", "Europe"), "QAT": ("Qatar", r"Qatar", "Moyen-Orient"),
    "ROU": ("Roumanie", r"Romania", "Europe"), "RUS": ("Russie", r"Russia", "Europe"),
    "RWA": ("Rwanda", r"Rwanda", "Afrique"), "SAU": ("Arabie saoudite", r"Saudi Arabia", "Moyen-Orient"),
    "SEN": ("Sénégal", r"Senegal", "Afrique"), "SRB": ("Serbie", r"Serbia", "Europe"),
    "SLE": ("Sierra Leone", r"Sierra Leone", "Afrique"), "SGP": ("Singapour", r"Singapore", "Asie"),
    "SVK": ("Slovaquie", r"Slovakia", "Europe"), "SVN": ("Slovénie", r"Slovenia", "Europe"),
    "SOM": ("Somalie", r"Somalia", "Afrique"), "ZAF": ("Afrique du Sud", r"South Africa", "Afrique"),
    "SSD": ("Soudan du Sud", r"South Sudan", "Afrique"), "SDN": ("Soudan", r"(?<!South )Sudan", "Afrique"),
    "ESP": ("Espagne", r"Spain", "Europe"), "LKA": ("Sri Lanka", r"Sri Lanka", "Asie"),
    "SWE": ("Suède", r"Sweden", "Europe"), "CHE": ("Suisse", r"Switzerland", "Europe"),
    "SYR": ("Syrie", r"Syria", "Moyen-Orient"), "TWN": ("Taïwan", r"Taiwan", "Asie"),
    "TZA": ("Tanzanie", r"Tanzania", "Afrique"), "THA": ("Thaïlande", r"Thailand", "Asie"),
    "TLS": ("Timor-Leste", r"Timor-Leste|East Timor|Timor", "Asie"), "TGO": ("Togo", r"Togo", "Afrique"),
    "TUN": ("Tunisie", r"Tunisia", "Afrique"), "TUR": ("Turquie", r"Turkey|Türkiye", "Moyen-Orient"),
    "UGA": ("Ouganda", r"Uganda", "Afrique"), "UKR": ("Ukraine", r"Ukraine", "Europe"),
    "ARE": ("Émirats arabes unis", r"United Arab Emirates|Emirates|UAE", "Moyen-Orient"),
    "GBR": ("Royaume-Uni", r"United Kingdom|Great Britain|England|Scotland|Wales|Northern Ireland", "Europe"),
    "USA": ("États-Unis", r"United States(?: of America)?|America(?!s)", "Amériques"),
    "URY": ("Uruguay", r"Uruguay", "Amériques"), "UZB": ("Ouzbékistan", r"Uzbekistan", "Asie"),
    "VEN": ("Venezuela", r"Venezuela", "Amériques"), "VNM": ("Viêt Nam", r"Viet ?[Nn]am", "Asie"),
    "YEM": ("Yémen", r"Yemen", "Moyen-Orient"), "ZMB": ("Zambie", r"Zambia", "Afrique"),
    "ZWE": ("Zimbabwe", r"Zimbabwe", "Afrique"),
}
NOM_PAYS = {iso: v[0] for iso, v in PAYS.items()}
CONTINENT = {iso: v[2] for iso, v in PAYS.items()}
_MOTIFS = {iso: re.compile(r"(?<![\w-])(?:" + v[1] + r")(?![\w-])") for iso, v in PAYS.items()}
_MOTIFS_I = {iso: re.compile(r"(?<![\w-])(?:" + v[1] + r")(?![\w-])", re.I) for iso, v in PAYS.items()}

# Lieux des titres de voyage et des en-têtes qui ne contiennent pas le nom du pays.
LIEUX = {
    "Rio de Janeiro": "BRA", "Aparecida": "BRA", "Holy Land": ["JOR", "ISR", "PSE"], "Amman": "JOR",
    "Bethlehem": "PSE", "Jerusalem": "ISR", "Tel Aviv": "ISR", "Tirana": "ALB", "Strasbourg": "FRA",
    "European Parliament": "FRA", "Council of Europe": "FRA", "Seoul": "KOR", "Daejeon": "KOR",
    "Haemi": "KOR", "Ankara": "TUR", "Istanbul": "TUR", "Colombo": "LKA", "Madhu": "LKA", "Manila": "PHL",
    "Tacloban": "PHL", "Palo": "PHL", "Sarajevo": "BIH", "Quito": "ECU", "Guayaquil": "ECU",
    "La Paz": "BOL", "El Alto": "BOL", "Santa Cruz": "BOL", "Palmasola": "BOL", "Asunción": "PRY",
    "Havana": "CUB", "Holguín": "CUB", "Santiago de Cuba": "CUB", "Washington": "USA", "New York": "USA",
    "Philadelphia": "USA", "United Nations": "USA", "Nairobi": "KEN", "Kampala": "UGA", "Namugongo": "UGA",
    "Bangui": "CAF", "Mexico City": "MEX", "Ecatepec": "MEX", "Chiapas": "MEX", "Morelia": "MEX",
    "Ciudad Juárez": "MEX", "Lesvos": "GRC", "Lesbos": "GRC", "Mytilene": "GRC", "Yerevan": "ARM",
    "Gyumri": "ARM", "Kraków": "POL", "Krakow": "POL", "Częstochowa": "POL", "Auschwitz": "POL",
    "Tbilisi": "GEO", "Mtskheta": "GEO", "Baku": "AZE", "Lund": "SWE", "Malmö": "SWE", "Cairo": "EGY",
    "Fátima": "PRT", "Fatima": "PRT", "Bogotá": "COL", "Villavicencio": "COL", "Medellín": "COL",
    "Cartagena": "COL", "Yangon": "MMR", "Nay Pyi Taw": "MMR", "Dhaka": "BGD", "Santiago": "CHL",
    "Temuco": "CHL", "Iquique": "CHL", "Lima": "PER", "Puerto Maldonado": "PER", "Trujillo": "PER",
    "Geneva": "CHE", "Dublin": "IRL", "Knock": "IRL", "Vilnius": "LTU", "Kaunas": "LTU", "Riga": "LVA",
    "Aglona": "LVA", "Tallinn": "EST", "Panama City": "PAN", "Abu Dhabi": "ARE", "Rabat": "MAR",
    "Sofia": "BGR", "Rakovski": "BGR", "Skopje": "MKD", "Bucharest": "ROU", "Iași": "ROU", "Iasi": "ROU",
    "Blaj": "ROU", "Maputo": "MOZ", "Antananarivo": "MDG", "Port Louis": "MUS", "Bangkok": "THA",
    "Tokyo": "JPN", "Nagasaki": "JPN", "Hiroshima": "JPN", "Baghdad": "IRQ", "Najaf": "IRQ", "Ur": "IRQ",
    "Erbil": "IRQ", "Mosul": "IRQ", "Qaraqosh": "IRQ", "Budapest": "HUN", "Bratislava": "SVK",
    "Prešov": "SVK", "Košice": "SVK", "Šaštin": "SVK", "Nicosia": "CYP", "Athens": "GRC",
    "Valletta": "MLT", "Gozo": "MLT", "Edmonton": "CAN", "Québec": "CAN",
    "Quebec": "CAN", "Iqaluit": "CAN", "Maskwacis": "CAN", "Nur-Sultan": "KAZ", "Astana": "KAZ",
    "Awali": "BHR", "Manama": "BHR", "Kinshasa": "COD", "Juba": "SSD", "Lisbon": "PRT", "Ulaanbaatar": "MNG",
    "Marseille": "FRA", "Dubai": "ARE", "Brussels": "BEL", "Leuven": "BEL",
    "Louvain": "BEL", "Laeken": "BEL", "Koekelberg": "BEL", "Jakarta": "IDN", "Port Moresby": "PNG",
    "Vanimo": "PNG", "Dili": "TLS", "Ajaccio": "FRA", "Corsica": "FRA",
}
_LIEUX = [(re.compile(r"(?<![\w-])" + re.escape(lieu) + r"(?![\w-])", re.I), iso) for lieu, iso in LIEUX.items()]


def pays_mentionnes(texte, ignorer_casse=False):
    """Compte des mentions par pays (dict ISO3 -> nombre)."""
    motifs = _MOTIFS_I if ignorer_casse else _MOTIFS
    comptes = {iso: len(m.findall(texte)) for iso, m in motifs.items()}
    return {iso: n for iso, n in comptes.items() if n}


def pays_du_lieu(texte):
    """Pays désignés dans un titre de voyage ou un libellé de lieu (noms de pays et lieux connus)."""
    trouves = set(pays_mentionnes(texte, ignorer_casse=True))
    for motif, iso in _LIEUX:
        if motif.search(texte):
            trouves |= set(iso if isinstance(iso, list) else [iso])
    return trouves - {"ITA"}


EN_VOL = re.compile(r"flight|aereo|plane", re.I)


def attribuer_pays(df):
    """Pays de chaque discours : lieu de l'en-tête, sinon pays unique du voyage, sinon même jour."""
    pays = []
    for venue, header, title, voyage in zip(df["venue_raw"], df["header"], df["title"], df["travel_title"]):
        if EN_VOL.search(venue) or re.search(r"in-flight|press conference", title, re.I):
            pays.append("EN_VOL")
            continue
        du_voyage = pays_du_lieu(voyage)
        candidats = (pays_du_lieu(venue) & du_voyage) or pays_du_lieu(venue)
        if len(candidats) != 1:
            # Ignorer la ligne « Apostolic Journey to X and Y » qui cite tous les pays.
            lignes = "\n".join(l for l in header.splitlines() if not re.search(r"journey|visit|pilgrimage", l, re.I))
            candidats = (pays_du_lieu(lignes) | pays_du_lieu(title)) & du_voyage
        if len(candidats) != 1 and len(du_voyage) == 1:
            candidats = du_voyage
        pays.append(next(iter(candidats)) if len(candidats) == 1 else "")
    s = pd.Series(pays, index=df.index)
    # Propagation : un discours sans pays prend celui des autres discours du même voyage le même jour.
    manquants = s.eq("")
    if manquants.any():
        connu = pd.DataFrame({"v": df["travel_title"], "d": df["date"], "p": s}).loc[~s.isin(["", "EN_VOL"])]
        jour = connu.groupby(["v", "d"])["p"].agg(lambda x: x.mode().iat[0])
        for i in s.index[manquants]:
            s[i] = jour.get((df.at[i, "travel_title"], df.at[i, "date"]), "")
    return s


# ---------------------------------------------------------------------------
# Type de public, d'après le titre (premier motif trouvé dans cet ordre).
# ---------------------------------------------------------------------------
PUBLICS = [
    ("Presse et vol", r"press conference|in-flight|journalists|interview|flight"),
    ("Autorités et diplomatie", r"authorit|civil society|diplomatic|president|parliament|congress|united nations|"
                                r"government|king|council of europe|state officials|political|public figures|"
                                r"world of (?:culture|labou?r|work|business)|leaders of|leaders gathered|"
                                r"municipal|town hall|golden book"),
    ("Œcuménisme et dialogue", r"ecumenic|interreligious|inter-religious|religious leaders|jewish|muslim|islam|"
                               r"orthodox|patriarch|imam|rabbi|lutheran|mosque|synagogue|interfaith|"
                               r"holy synod|catholicos|sheikh|grand mufti|council of elders|chief rabbinate|"
                               r"joint declaration|divine liturgy|evangelical|buddhis|sangha|al-azhar|peace conference|"
                               r"assyrian|chaldean"),
    ("Évêques", r"bishop|episcopal|cardinal|celam|ordinar"),
    ("Clergé et religieux", r"priest|clergy|religious|seminarian|consecrated|pastoral (?:agent|worker)|catechist|"
                            r"jesuit|deacon|novice|nuns|sisters|brothers of"),
    ("Jeunes et éducation", r"young|youth|student|universit|school|children|vigil"),
    ("Pauvres, malades, migrants", r"poor|sick|hospital|refugee|migrant|prison|penitentiar|inmate|detain|homeless|"
                                   r"disabl|charit|victim|elderly|orphan|caritas|needy|displaced|indigenous|"
                                   r"workers|slum|community of varginha|bañado|medical staff|rehabilitation|popular movements|"
                                   r"roma? community|akamasoa|casa hogar|bethlehem center"),
    ("Familles", r"famil"),
    ("Prière, mémoire, réconciliation", r"shrine|marian|prayer|basilica|cathedral|chapel|candles|memorial|"
                                        r"yad vashem|genocide|cemetery|holocaust|auschwitz|peace park|tomb|wall|"
                                        r"reconciliation|nuclear|atomic|martyr|in memory"),
    ("Accueil et départ", r"welcom|farewell|departure|arrival|greeting to (?:the )?(?:people|faithful|crowd)|"
                          r"those gathered|population"),
]
ORDRE_PUBLICS = [p for p, _ in PUBLICS] + ["Autres rencontres"]


def type_public(titre):
    for nom, motif in PUBLICS:
        if re.search(motif, titre, re.I):
            return nom
    return "Autres rencontres"


# ---------------------------------------------------------------------------
# Texte : mots, mots-outils, lexiques thématiques, références.
# ---------------------------------------------------------------------------
MOT = re.compile(r"[^\W\d_]+(?:[-’'][^\W\d_]+)*")


def mots(texte):
    """Mots en minuscules ; « people's » -> « people »."""
    return [re.sub(r"'s$", "", m) for m in MOT.findall(texte.lower().replace("’", "'"))]


def _stopwords():
    from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS
    extra = """also would could may might must shall let us one two many much like really even yet
    ever every today thank thanks thus therefore indeed always never way things thing make made
    know want see say said go come take give dear brother brothers sister sisters friend friends
    holy father pope francis mr mrs ladies gentlemen excellency excellencies yes did does doing tell
    don't it's i'm we're that's let's can't won't isn't there's we've you're they're i've"""
    return set(ENGLISH_STOP_WORDS) | set(extra.split())


STOPWORDS = _stopwords()

LEXIQUE = {
    "Paix et guerre": r"\bpeace\w*|\bwars?\b|\bweapons?\b|\barms\b|\bconflicts?\b|\bnuclear\b|\bviolence\b",
    "Migrants et réfugiés": r"\bmigra\w*|\brefugees?\b|\bexiles?\b|\bdisplaced\b|\basylum\b",
    "Pauvreté et exclusion": r"\bpoor\b|\bpoverty\b|\bexclu\w*|\bthrowaway\b|\bmarginali\w*|\binequalit\w*",
    "Écologie et création": r"\becolog\w*|\bcommon home\b|\bclimate\b|\benvironment\w*|\bplanet\b|\bcreation\b",
    "Miséricorde et pardon": r"\bmerc(?:y|iful)\b|\bforgive\w*|\bpardon\b",
    "Famille": r"\bfamil(?:y|ies)\b|\bmarriage\b|\bspouses\b|\bparents\b",
    "Jeunes": r"\byoung people\b|\byouth\b|\byoung\b",
    "Personnes âgées": r"\bgrandparents\b|\belderly\b|\bold age\b|\bgrandmothers?\b",
    "Dialogue interreligieux": r"\binterreligious\b|\bmuslims?\b|\bislam\w*|\bjews?\b|\bjewish\b|\becumeni\w*|\bfraternity\b",
    "Corruption et justice": r"\bcorrupt\w*|\bjustice\b|\bunjust\w*|\bimpunity\b",
    "Économie et travail": r"\beconom\w*|\bmoney\b|\bfinanc\w*|\bmarkets?\b|\bwork(?:ers?)?\b|\bjobs?\b|\bunemploy\w*",
    "Dignité humaine": r"\bdignity\b|\bhuman rights\b",
    "Mémoire et réconciliation": r"\bmemory\b|\breconcil\w*|\bwounds?\b|\bmartyrs?\b",
    "Joie et espérance": r"\bjoy\w*|\bhope\w*",
    "Église en sortie": r"\bmission\w*|\bevangeli\w*|\bperipher\w*|\bgo(?:ing)? out\b",
    "Abus": r"\babuses?\b|\bsexual abuse\b",
}

REFERENCES = {
    "Benoît XVI": r"Benedict XVI",
    "Jean-Paul II": r"John Paul II",
    "Paul VI": r"\bPaul VI\b",
    "Jean XXIII": r"John XXIII",
    "Vatican II": r"Second Vatican Council|Vatican II|Gaudium et Spes|Lumen Gentium",
    "François d'Assise": r"Francis of Assisi",
    "Ignace de Loyola": r"Ignatius",
    "Mère Teresa": r"Mother Teresa|Teresa of Calcutta",
    "Evangelii gaudium": r"Evangelii Gaudium",
    "Laudato si'": r"Laudato Si",
    "Amoris laetitia": r"Amoris Laetitia",
    "Fratelli tutti": r"Fratelli Tutti",
    "Document d'Abou Dhabi": r"Document on Human Fraternity|Abu Dhabi Document",
}


# ---------------------------------------------------------------------------
# Chargement.
# ---------------------------------------------------------------------------
def nom_voyage(titre):
    """« Apostolic Journey of the Holy Father to Kenya, Uganda ... (25-30 November 2015) » -> « Kenya, Uganda ... 2015 »."""
    annee = re.findall(r"\d{4}", titre)
    court = re.sub(r"\s*\([^()]*\d{4}\s*\)\s*$", "", titre)
    court = re.sub(r"^.*?\b(?:to|in)\s+(?:the\s+)?", "", court, count=1)
    court = re.sub(r"\s*,?\s*(?:on the occasion|for the|and visit to|\(Ecumenical|, \d+\w* World).*$", "", court, flags=re.I)
    court = re.sub(r",? (?:and )?to (?:the )?", ", ", court)
    court = re.sub(r"Republic of |Kingdom of |United States of America", lambda m: "USA" if "United" in m.group() else "", court)
    court = court.replace("Shrine of Our Lady of ", "").replace("European Parliament and the Council of Europe", "Strasbourg")
    if len(court) > 40:
        court = court[:38].rsplit(" ", 1)[0] + "…"
    return f"{court} {annee[-1] if annee else ''}".strip()


def charger():
    if not CORPUS.exists():
        sys.exit("Exécuter telecharger_discours.py puis preparer_corpus.py ; voir README.")
    df = pd.read_json(CORPUS, lines=True, dtype={"date": str})
    if df.duplicated(["event_id", "language"]).any():
        raise ValueError("Doublons événement/langue : examiner le corpus avant l'analyse.")
    for col in ["text", "header", "venue_raw", "title", "travel_title"]:
        df[col] = df[col].fillna("") if col in df else ""
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["annee"] = df["date"].dt.year.astype("Int64")
    df["titre"] = df["title"].str.replace(r"\s*\|.*$", "", regex=True)
    df["voyage"] = df["travel_title"].map(nom_voyage)
    df["n_mots"] = df["text"].map(lambda t: len(mots(t)))
    df["iso"] = attribuer_pays(df)
    df["en_vol"] = df["iso"].eq("EN_VOL")
    df["pays"] = df["iso"].map(NOM_PAYS).fillna(df["iso"].map({"EN_VOL": "En vol", "": "Inconnu"}))
    df["continent"] = pd.Categorical(df["iso"].map(CONTINENT), ORDRE_CONTINENTS, ordered=True)
    publics = df["titre"].map(type_public).where(~df["en_vol"], "Presse et vol")
    df["public"] = pd.Categorical(publics, ORDRE_PUBLICS, ordered=True)
    return df.sort_values(["date", "event_id"]).reset_index(drop=True)


def taux_lexique(df, groupe, lexique=LEXIQUE):
    """Occurrences pour 10 000 mots, par groupe et par thème."""
    occ = pd.DataFrame({nom: df["text"].map(lambda t, rx=re.compile(motif, re.I): len(rx.findall(t)))
                        for nom, motif in lexique.items()}, index=df.index)
    occ[groupe] = df[groupe]
    sommes = occ.groupby(groupe, observed=True).sum()
    total = df.groupby(groupe, observed=True)["n_mots"].sum()
    return sommes.div(total, axis=0) * 10_000


def log_odds(compte_a, compte_b, prior):
    """Log-odds pondéré avec a priori de Dirichlet informatif (Monroe et al., 2008).

    Renvoie un score z par mot : > 0 caractéristique de A, < 0 de B.
    """
    a0, n_a, n_b = prior.sum(), compte_a.sum(), compte_b.sum()
    la = np.log((compte_a + prior) / (n_a + a0 - compte_a - prior))
    lb = np.log((compte_b + prior) / (n_b + a0 - compte_b - prior))
    var = 1 / (compte_a + prior) + 1 / (compte_b + prior)
    return (la - lb) / np.sqrt(var)
