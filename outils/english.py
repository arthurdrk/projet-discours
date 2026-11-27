"""English labels for the English report.

The analysis module (analyse_corpus.py) names continents, audiences and themes in French.
translate() gives the speeches table English labels, and LEXICON is the same list of
themes as analyse_corpus.LEXIQUE with English names.
"""
import geonamescache

import analyse_corpus as ac
import graphiques as g

CONTINENTS = {
    "Europe": "Europe", "Amériques": "Americas", "Asie": "Asia",
    "Moyen-Orient": "Middle East", "Afrique": "Africa", "Océanie": "Oceania",
}
CONTINENT_ORDER = [CONTINENTS[c] for c in ac.ORDRE_CONTINENTS]
CONTINENT_COLORS = {CONTINENTS[c]: color for c, color in g.COULEUR_CONTINENT.items()}

AUDIENCES = {
    "Autorités et diplomatie": "Authorities and diplomats",
    "Œcuménisme et dialogue": "Ecumenical and interreligious",
    "Évêques": "Bishops",
    "Clergé et religieux": "Clergy and religious",
    "Jeunes et éducation": "Young people and students",
    "Pauvres, malades, migrants": "The poor, the sick, migrants",
    "Familles": "Families",
    "Prière, mémoire, réconciliation": "Prayer and memory",
    "Accueil et départ": "Welcome and farewell",
    "Autres rencontres": "Other meetings",
}

THEMES = {
    "Paix et guerre": "Peace and war",
    "Migrants et réfugiés": "Migrants and refugees",
    "Pauvreté et exclusion": "Poverty and exclusion",
    "Écologie et création": "Ecology and creation",
    "Miséricorde et pardon": "Mercy and forgiveness",
    "Famille": "Family",
    "Jeunes": "Young people",
    "Personnes âgées": "The elderly",
    "Dialogue interreligieux": "Interreligious dialogue",
    "Corruption et justice": "Corruption and justice",
    "Économie et travail": "Economy and work",
    "Dignité humaine": "Human dignity",
    "Mémoire et réconciliation": "Memory and reconciliation",
    "Joie et espérance": "Joy and hope",
    "Église en sortie": "Missionary Church",
}
LEXICON = {THEMES[theme]: pattern for theme, pattern in ac.LEXIQUE.items()}

# English country names, from their ISO3 code
COUNTRY_NAMES = {c["iso3"]: c["name"] for c in geonamescache.GeonamesCache().get_countries().values()}
COUNTRY_NAMES.update({"PSE": "Palestine", "TLS": "Timor-Leste", "CIV": "Côte d'Ivoire"})


def translate(df):
    """Speeches table with English names for the country, the continent and the audience."""
    return df.assign(pays=df["iso"].map(COUNTRY_NAMES),
                     continent=df["continent"].map(CONTINENTS),
                     public=df["public"].map(AUDIENCES))
