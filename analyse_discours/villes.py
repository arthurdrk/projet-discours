"""Rattacher chaque discours à une ville, avec ses coordonnées.

Les mots-clés sont ceux de la table LIEUX_VERS_PAYS de pays.py (en minuscules).
Pour chaque mot-clé de ville : (nom affiché, latitude, longitude, capitale ?)
"capitale" veut dire capitale du pays (siège du gouvernement).

Règles pour trouver la ville d'un discours :
1. Discours au Vatican ou à Rome -> "Rome / Vatican".
2. Discours dans l'avion -> pas de ville.
3. Sinon, on cherche un mot-clé de ville dans le lieu et la parenthèse finale du
   titre, puis dans la fin du titre, puis dans la ligne du voyage.
   Si on n'en trouve pas, la ville reste inconnue (None) : on ne remplace PAS par
   la capitale du pays, sinon on fausserait la question « ne va-t-il que dans les capitales ? ».

Lancer ce fichier affiche le bilan capitales / autres villes :
    python analyse_discours/villes.py
"""
import re

from pays import parenthese_finale

ROME = "Rome / Vatican"

VILLES = {
    # Rome (la "salle Bologne" est une salle du Vatican)
    "salle bologne": (ROME, 41.90, 12.45, True),
    # Le « Centre Bethléem » est un foyer à Bratislava
    "centre bethléem": ("Bratislava", 48.15, 17.11, True),
    # Italie
    "assise": ("Assise", 43.07, 12.62, False),
    "ariccia": ("Ariccia", 41.72, 12.67, False),
    "naples": ("Naples", 40.85, 14.27, False),
    "pompéi": ("Pompéi", 40.75, 14.49, False),
    "milan": ("Milan", 45.46, 9.19, False),
    "turin": ("Turin", 45.07, 7.69, False),
    "gênes": ("Gênes", 44.41, 8.93, False),
    "florence": ("Florence", 43.77, 11.26, False),
    "prato": ("Prato", 43.88, 11.10, False),
    "bologne": ("Bologne", 44.49, 11.34, False),
    "cesena": ("Cesena", 44.14, 12.24, False),
    "cagliari": ("Cagliari", 39.22, 9.12, False),
    "caserte": ("Caserte", 41.07, 14.33, False),
    "cosenza": ("Cosenza", 39.30, 16.25, False),
    "cassano": ("Cassano all'Ionio", 39.78, 16.32, False),
    "lampedusa": ("Lampedusa", 35.51, 12.60, False),
    "greccio": ("Greccio", 42.45, 12.76, False),
    "loppiano": ("Loppiano", 43.67, 11.43, False),
    "nomadelfia": ("Nomadelfia", 42.78, 11.15, False),
    "carpi": ("Carpi", 44.78, 10.88, False),
    "mirandola": ("Mirandola", 44.89, 11.07, False),
    "campobasso": ("Campobasso", 41.56, 14.66, False),
    "isernia": ("Isernia", 41.59, 14.23, False),
    "castelpetroso": ("Castelpetroso", 41.56, 14.35, False),
    "palerme": ("Palerme", 38.12, 13.36, False),
    "venise": ("Venise", 45.44, 12.32, False),
    "vérone": ("Vérone", 45.44, 10.99, False),
    "l'aquila": ("L'Aquila", 42.35, 13.40, False),
    "l’aquila": ("L'Aquila", 42.35, 13.40, False),   # avec l'apostrophe typographique
    "pietrelcina": ("Pietrelcina", 41.20, 14.85, False),
    "san giovanni rotondo": ("San Giovanni Rotondo", 41.71, 15.73, False),
    "bari": ("Bari", 41.12, 16.87, False),
    "matera": ("Matera", 40.67, 16.60, False),
    "trieste": ("Trieste", 45.65, 13.78, False),
    # Europe
    "strasbourg": ("Strasbourg", 48.58, 7.75, False),
    "marseille": ("Marseille", 43.30, 5.37, False),
    "ajaccio": ("Ajaccio", 41.93, 8.74, False),
    "corse": ("Ajaccio", 41.93, 8.74, False),
    "genève": ("Genève", 46.20, 6.14, False),
    "coe": ("Genève", 46.20, 6.14, False),        # Conseil œcuménique des Églises
    "tirana": ("Tirana", 41.33, 19.82, True),
    "sarajevo": ("Sarajevo", 43.86, 18.41, True),
    "istanbul": ("Istanbul", 41.01, 28.98, False),
    "ankara": ("Ankara", 39.93, 32.86, True),
    "cracovie": ("Cracovie", 50.06, 19.94, False),
    "częstochowa": ("Częstochowa", 50.81, 19.12, False),
    "auschwitz": ("Auschwitz", 50.03, 19.20, False),
    "malmö": ("Malmö", 55.60, 13.00, False),
    "lund": ("Lund", 55.70, 13.19, False),
    "fátima": ("Fátima", 39.63, -8.67, False),
    "fatima": ("Fátima", 39.63, -8.67, False),
    "lisbonne": ("Lisbonne", 38.72, -9.14, True),
    "dublin": ("Dublin", 53.35, -6.26, True),
    "knock": ("Knock", 53.79, -8.92, False),
    "vilnius": ("Vilnius", 54.69, 25.28, True),
    "kaunas": ("Kaunas", 54.90, 23.90, False),
    "riga": ("Riga", 56.95, 24.11, True),
    "aglona": ("Aglona", 56.13, 27.01, False),
    "tallinn": ("Tallinn", 59.44, 24.75, True),
    "sofia": ("Sofia", 42.70, 23.32, True),
    "rakovski": ("Rakovski", 42.27, 24.97, False),
    "rakovsky": ("Rakovski", 42.27, 24.97, False),
    "skopje": ("Skopje", 42.00, 21.43, True),
    "bucarest": ("Bucarest", 44.43, 26.10, True),
    "iasi": ("Iași", 47.16, 27.59, False),
    "blaj": ("Blaj", 46.18, 23.92, False),
    "la valette": ("La Valette", 35.90, 14.51, True),
    "gozo": ("Gozo", 36.04, 14.24, False),
    "nicosie": ("Nicosie", 35.17, 33.36, True),
    "athènes": ("Athènes", 37.98, 23.73, True),
    "lesbos": ("Lesbos (Mytilène)", 39.11, 26.55, False),
    "mytilène": ("Lesbos (Mytilène)", 39.11, 26.55, False),
    "budapest": ("Budapest", 47.50, 19.04, True),
    "bratislava": ("Bratislava", 48.15, 17.11, True),
    "prešov": ("Prešov", 49.00, 21.24, False),
    "košice": ("Košice", 48.72, 21.26, False),
    "šaštin": ("Šaštín", 48.64, 17.15, False),
    "luxembourg": ("Luxembourg", 49.61, 6.13, True),
    "bruxelles": ("Bruxelles", 50.85, 4.35, True),
    "louvain": ("Louvain", 50.88, 4.70, False),
    # Moyen-Orient et Caucase
    "amman": ("Amman", 31.95, 35.93, True),
    "bethléem": ("Bethléem", 31.70, 35.20, False),
    # Jérusalem : capitale proclamée par Israël, statut contesté
    "jérusalem": ("Jérusalem", 31.78, 35.22, True),
    "tel aviv": ("Tel Aviv", 32.09, 34.78, False),
    "le caire": ("Le Caire", 30.04, 31.24, True),
    "caire": ("Le Caire", 30.04, 31.24, True),
    "erevan": ("Erevan", 40.18, 44.51, True),
    "yerevan": ("Erevan", 40.18, 44.51, True),
    "etchmiadzin": ("Etchmiadzin", 40.16, 44.29, False),
    "gyumri": ("Gyumri", 40.79, 43.85, False),
    "tbilissi": ("Tbilissi", 41.72, 44.79, True),
    "mtskheta": ("Mtskheta", 41.85, 44.72, False),
    "bakou": ("Bakou", 40.41, 49.87, True),
    "abou dabi": ("Abou Dabi", 24.45, 54.38, True),
    "rabat": ("Rabat", 34.02, -6.84, True),
    "bagdad": ("Bagdad", 33.31, 44.36, True),
    "erbil": ("Erbil", 36.19, 44.01, False),
    "mossoul": ("Mossoul", 36.34, 43.13, False),
    "qaraqosh": ("Qaraqosh", 36.27, 43.38, False),
    "nadjaf": ("Nadjaf", 32.03, 44.35, False),
    "ur": ("Ur", 30.96, 46.10, False),
    "awali": ("Awali", 26.08, 50.55, False),
    "manama": ("Manama", 26.23, 50.59, True),
    "sakhir": ("Sakhir", 26.03, 50.52, False),
    "noursoultan": ("Astana", 51.17, 71.45, True),
    "nour-soultan": ("Astana", 51.17, 71.45, True),
    "astana": ("Astana", 51.17, 71.45, True),
    # Asie
    "séoul": ("Séoul", 37.57, 126.98, True),
    "solmoe": ("Solmoe", 36.88, 126.77, False),
    "haemi": ("Haemi", 36.71, 126.55, False),
    "kkottongnae": ("Kkottongnae", 36.94, 127.69, False),
    "daejeon": ("Daejeon", 36.35, 127.38, False),
    "colombo": ("Colombo", 6.93, 79.86, True),
    "madhu": ("Madhu", 8.86, 80.20, False),
    "manille": ("Manille", 14.60, 120.98, True),
    "tacloban": ("Tacloban", 11.24, 125.00, False),
    "palo": ("Palo", 11.16, 124.99, False),
    "yangon": ("Yangon", 16.84, 96.17, False),
    "nay pyi taw": ("Nay Pyi Taw", 19.76, 96.08, True),
    "dhaka": ("Dhaka", 23.81, 90.41, True),
    "bangkok": ("Bangkok", 13.76, 100.50, True),
    "tokyo": ("Tokyo", 35.68, 139.69, True),
    "nagasaki": ("Nagasaki", 32.75, 129.88, False),
    "hiroshima": ("Hiroshima", 34.39, 132.46, False),
    "oulan-bator": ("Oulan-Bator", 47.89, 106.91, True),
    "jakarta": ("Jakarta", -6.21, 106.85, True),
    "port moresby": ("Port Moresby", -9.44, 147.18, True),
    "vanimo": ("Vanimo", -2.69, 141.30, False),
    "dili": ("Dili", -8.56, 125.57, True),
    "singapour": ("Singapour", 1.35, 103.82, True),
    # Afrique
    "nairobi": ("Nairobi", -1.29, 36.82, True),
    "u.n.o.n": ("Nairobi", -1.29, 36.82, True),   # Office des Nations unies à Nairobi
    "kampala": ("Kampala", 0.35, 32.58, True),
    "entebbe": ("Entebbe", 0.05, 32.46, False),
    "namugongo": ("Namugongo", 0.39, 32.65, False),
    "munyonyo": ("Munyonyo", 0.25, 32.62, False),
    "bangui": ("Bangui", 4.39, 18.56, True),
    "maputo": ("Maputo", -25.97, 32.57, True),
    "antananarivo": ("Antananarivo", -18.88, 47.51, True),
    "port louis": ("Port-Louis", -20.16, 57.50, True),
    "kinshasa": ("Kinshasa", -4.32, 15.31, True),
    "djouba": ("Djouba", 4.85, 31.58, True),
    "juba": ("Djouba", 4.85, 31.58, True),
    # Amériques
    "rio de janeiro": ("Rio de Janeiro", -22.91, -43.17, False),
    "aparecida": ("Aparecida", -22.85, -45.23, False),
    "quito": ("Quito", -0.18, -78.47, True),
    "guayaquil": ("Guayaquil", -2.19, -79.89, False),
    "quinche": ("El Quinche", -0.11, -78.30, False),
    "la paz": ("La Paz", -16.50, -68.15, True),
    "el alto": ("El Alto", -16.50, -68.19, False),
    "santa cruz": ("Santa Cruz", -17.78, -63.18, False),
    "palmasola": ("Santa Cruz", -17.78, -63.18, False),   # prison de Santa Cruz
    "asunción": ("Asunción", -25.26, -57.58, True),
    "caacupé": ("Caacupé", -25.39, -57.14, False),
    "la havane": ("La Havane", 23.11, -82.37, True),
    "holguín": ("Holguín", 20.89, -76.26, False),
    "santiago de cuba": ("Santiago de Cuba", 20.02, -75.83, False),
    "washington": ("Washington", 38.90, -77.04, True),
    "new york": ("New York", 40.71, -74.01, False),
    "onu": ("New York", 40.71, -74.01, False),
    "philadelphie": ("Philadelphie", 39.95, -75.17, False),
    "mexico": ("Mexico", 19.43, -99.13, True),
    "juárez": ("Ciudad Juárez", 31.69, -106.42, False),
    "morelia": ("Morelia", 19.70, -101.19, False),
    "tuxtla": ("Tuxtla Gutiérrez", 16.75, -93.12, False),
    "ecatepec": ("Ecatepec", 19.60, -99.05, False),
    "chiapas": ("San Cristóbal de las Casas", 16.74, -92.64, False),
    "bogota": ("Bogota", 4.71, -74.07, True),
    "bogotá": ("Bogota", 4.71, -74.07, True),
    "medellín": ("Medellín", 6.24, -75.58, False),
    "villavicencio": ("Villavicencio", 4.14, -73.63, False),
    "carthagène": ("Carthagène", 10.39, -75.48, False),
    "santiago": ("Santiago du Chili", -33.45, -70.67, True),
    "hurtado": ("Santiago du Chili", -33.45, -70.67, True),  # sanctuaire Saint-Albert-Hurtado
    "temuco": ("Temuco", -38.74, -72.60, False),
    "iquique": ("Iquique", -20.21, -70.15, False),
    "lima": ("Lima", -12.05, -77.04, True),
    "trujillo": ("Trujillo", -8.11, -79.03, False),
    "puerto maldonado": ("Puerto Maldonado", -12.59, -69.19, False),
    "panamá": ("Panama", 8.98, -79.52, True),
    "panama": ("Panama", 8.98, -79.52, True),
    "edmonton": ("Edmonton", 53.55, -113.49, False),
    "québec": ("Québec", 46.81, -71.21, False),
    "iqaluit": ("Iqaluit", 63.75, -68.52, False),
    "maskwacis": ("Maskwacis", 52.83, -113.43, False),
}

# Position, capitale... à partir du nom affiché d'une ville
INFOS_VILLES = {nom: (lat, lon, capitale) for nom, lat, lon, capitale in VILLES.values()}

# Les mots-clés les plus longs d'abord ("santiago de cuba" avant "santiago")
MOTS_CLES_TRIES = sorted(VILLES, key=len, reverse=True)


def villes_citees(texte):
    """Renvoie les villes citées dans le texte, dans leur ordre d'apparition."""
    texte = texte.lower()
    trouvees = []   # liste de (position dans le texte, nom de la ville)
    for mot_cle in MOTS_CLES_TRIES:
        resultat = re.search(rf"\b{re.escape(mot_cle)}\b", texte)
        if resultat:
            trouvees.append((resultat.start(), VILLES[mot_cle][0]))
            # on efface le mot-clé (même longueur) pour que "santiago" ne retrouve
            # pas "santiago de cuba", sans décaler les positions
            texte = texte.replace(mot_cle, " " * len(mot_cle))
    trouvees.sort()
    return [nom for _, nom in trouvees]


def ville_du_discours(d):
    """La ville d'un discours, ou None si on ne la trouve pas.

    d doit déjà avoir sa clé "pays" (voir statistiques.preparer_discours).
    """
    if d["pays"] == "Vatican / Rome":
        return ROME
    if d["pays"] == "Avion":
        return None
    # On cherche du plus fiable au moins fiable : le lieu et la date entre
    # parenthèses, puis la fin du titre, puis l'intitulé du voyage
    for texte in [d["lieu"] + " " + parenthese_finale(d["titre"]),
                  d["titre"].split(":")[-1],
                  d["voyage"]]:
        villes = villes_citees(texte)
        if villes:
            return villes[0]
    return None


def bilan_capitales(discours):
    """Part des discours prononcés dans une capitale, hors Rome et hors Italie.

    Renvoie un dictionnaire de chiffres (affiché dans le globe et par ce fichier).
    """
    a_l_etranger = [d for d in discours if d["pays"] not in ("Vatican / Rome", "Italie", "Avion")]
    avec_ville = [d for d in a_l_etranger if d["ville"] is not None]
    en_capitale = [d for d in avec_ville if INFOS_VILLES[d["ville"]][2]]
    villes = {d["ville"] for d in avec_ville}
    capitales = {v for v in villes if INFOS_VILLES[v][2]}
    return {
        "discours_etranger": len(a_l_etranger),
        "discours_ville_connue": len(avec_ville),
        "discours_en_capitale": len(en_capitale),
        "pct_en_capitale": round(100 * len(en_capitale) / len(avec_ville), 1) if avec_ville else 0,
        "villes": len(villes),
        "capitales": len(capitales),
    }


if __name__ == "__main__":
    from collections import Counter

    from chercher_mot import charger_discours
    from statistiques import preparer_discours

    discours = preparer_discours(charger_discours())
    print(bilan_capitales(discours))
    print(Counter(d["ville"] for d in discours).most_common(30))
    sans_ville = [d for d in discours if d["ville"] is None and d["pays"] != "Avion"]
    print(f"\n{len(sans_ville)} discours sans ville trouvée :")
    for d in sans_ville:
        print(" ", d["pays"], "|", d["titre"][:90])
