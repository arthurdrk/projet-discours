"""Rattacher chaque pays à un continent.

Le Vatican et Rome sont gardés à part : c'est là que le pape prononce la plupart
de ses discours, on s'en sert comme point de comparaison.
Le Moyen-Orient est séparé de l'Asie, et la seule visite en Océanie
(Papouasie-Nouvelle-Guinée) est rangée avec l'Asie.

Utilisation :
    from continents import continent_du_pays
    continent_du_pays("Kenya")   # "Afrique"
"""

CONTINENTS = {
    "Vatican / Rome": ["Vatican / Rome"],
    "Europe": ["Italie", "Pologne", "Portugal", "France", "Slovaquie", "Hongrie", "Grèce",
               "Irlande", "Roumanie", "Belgique", "Albanie", "Bosnie-Herzégovine", "Lituanie",
               "Bulgarie", "Chypre", "Lettonie", "Estonie", "Macédoine du Nord", "Suisse",
               "Malte", "Luxembourg", "Suède"],
    "Amériques": ["Brésil", "États-Unis", "Mexique", "Colombie", "Pérou", "Bolivie", "Paraguay",
                  "Chili", "Panama", "Équateur", "Canada", "Cuba"],
    "Afrique": ["Kenya", "RD Congo", "Ouganda", "Centrafrique", "Madagascar", "Maroc",
                "Mozambique", "Soudan du Sud", "Maurice"],
    "Moyen-Orient": ["Israël", "Palestine", "Jordanie", "Turquie", "Égypte", "Bahreïn",
                     "Émirats arabes unis", "Irak"],
    "Asie et Océanie": ["Japon", "Corée du Sud", "Thaïlande", "Bangladesh", "Philippines",
                        "Myanmar", "Kazakhstan", "Mongolie", "Indonésie", "Timor oriental",
                        "Sri Lanka", "Singapour", "Géorgie", "Arménie", "Azerbaïdjan",
                        "Papouasie-Nouvelle-Guinée"],
}

# Dictionnaire inverse : pays -> continent
PAYS_VERS_CONTINENT = {pays: continent for continent, liste in CONTINENTS.items() for pays in liste}


def continent_du_pays(pays):
    """Renvoie le continent du pays, ou None (discours dans l'avion, pays inconnu)."""
    return PAYS_VERS_CONTINENT.get(pays)
