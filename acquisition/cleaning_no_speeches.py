"""Turn the raw "Place" strings of papal trips into one row per visited country.

Input : avibert/diffusion/df_trips.parquet  (columns Pope, Year, Place)
Output: avibert/diffusion/df_trips_countries.parquet / .csv
        (columns Pope, Year, Place, Country, ISO3)

`Country` uses the geonamescache country names and `ISO3` the ISO 3166-1
alpha-3 code, which is what plotly / geopandas expect to draw choropleth maps.
"""

import re
import unicodedata

import geonamescache
import pandas as pd
import s3fs

gc = geonamescache.GeonamesCache()
COUNTRIES = gc.get_countries()  # {"FR": {"name": "France", "iso3": "FRA", ...}, ...}
NAME_TO_ISO3 = {c["name"].strip(): c["iso3"] for c in COUNTRIES.values()}

# Names used on the Vatican website that differ from the geonamescache names,
# plus places (cities, regions, shrines...) that appear without their country.
ALIASES = {
    # Historical / alternative country names
    "United States of America": "United States",
    "USA": "United States",
    "Great Britain": "United Kingdom",
    "Federal Republic of Germany": "Germany",
    "Netherlands": "The Netherlands",
    "Czech Republic": "Czechia",
    "Czech and Slovak Federative Republic": ["Czechia", "Slovakia"],
    "Republic of Korea": "South Korea",
    "Korea": "South Korea",
    "Zaire": "Democratic Republic of the Congo",
    "Democratic Republic of Congo": "Democratic Republic of the Congo",
    "Swaziland": "Eswatini",
    "Cape Verde": "Cabo Verde",
    "Guinea Bissau": "Guinea-Bissau",
    "Trinidad-Tobago": "Trinidad and Tobago",
    "Fiji Islands": "Fiji",
    "Timor-Leste": "Timor Leste",
    "La Reunion": "Reunion",
    "Bahrein": "Bahrain",
    "Holy Land": "Israel",
    # Cities, regions and landmarks
    "Anchorage": "United States",
    "Denver": "United States",
    "St. Louis": "United States",
    "Paris": "France",
    "Lisieux": "France",
    "Lourdes": "France",
    "Marseille": "France",
    "Ajaccio": "France",
    "European Parliament": "France",  # Strasbourg
    "Geneva": "Switzerland",
    "Bern": "Switzerland",
    "Zaragoza": "Spain",
    "Santiago de Compostela": "Spain",
    "Valencia": "Spain",
    "Barcelona": "Spain",
    "Madrid": "Spain",
    "Santo Domingo": "Dominican Republic",
    "Lima": "Peru",
    "Yamoussoukro": "Ivory Coast",
    "Khartoum": "Sudan",
    "Sarajevo": "Bosnia and Herzegovina",
    "New Delhi": "India",
    "Fatima": "Portugal",
    "Mount Sinai": "Egypt",
    "Toronto": "Canada",
    "Cologne": "Germany",
    "Munchen": "Germany",
    "Regensburg": "Germany",
    "Dubai": "United Arab Emirates",
    "Budapest": "Hungary",
    "Rio de Janeiro": "Brazil",
    "Italian": "Italy",
    "Rome": "Italy",
}

# Trips whose description does not name any place we can map.
MANUAL_OVERRIDES = {
    "Africa": [  # John Paul II, May 1980
        "Democratic Republic of the Congo", "Republic of the Congo", "Kenya",
        "Ghana", "Burkina Faso", "Ivory Coast",
    ],
    "Apostolic Journey to the Far East and Mauritius (October 6-16, 1989)": [
        "South Korea", "Indonesia", "Mauritius",
    ],
}

# Italian places mentioned without "Italy" that geonames does not resolve.
ITALIAN_PLACES = [
    "Emilia Romagna", "Romagna", "Aosta Valley", "Friuli-Venezia Giulia", "Molise",
    "Valnerina", "Lombardy", "Veneto", "Gran Sasso", "Marches", "Fonte Avellana",
    "Collevalenza", "Feltre-Belluno", "Camaldoli", "La Verna", "Pompei",
    "Otranto", "Subiaco", "Loreto", "Siena", "Ischia", "Rimini",
]


def strip_accents(text):
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))


def build_matcher():
    """Map every lower-cased searchable name to a list of country names."""
    lookup = {name.casefold(): [name] for name in NAME_TO_ISO3}
    for alias, target in ALIASES.items():
        lookup[strip_accents(alias).casefold()] = target if isinstance(target, list) else [target]
    for place in ITALIAN_PLACES:
        lookup[place.casefold()] = ["Italy"]
    # Longest names first so "Papua New Guinea" wins over "Guinea", "South Sudan" over "Sudan"...
    names = sorted(lookup, key=len, reverse=True)
    pattern = re.compile(r"\b(" + "|".join(re.escape(n) for n in names) + r")\b", re.IGNORECASE)
    return lookup, pattern


LOOKUP, PATTERN = build_matcher()

ITALIAN_CITIES = {
    strip_accents(name).casefold()
    for city in gc.get_cities().values() if city["countrycode"] == "IT"
    for name in {city["name"], *city["alternatenames"]} if name
}


def place_to_countries(place):
    """Return the ordered, de-duplicated list of countries mentioned in a Place string."""
    if place in MANUAL_OVERRIDES:
        return MANUAL_OVERRIDES[place]
    text = strip_accents(place)
    found = []
    for match in PATTERN.finditer(text):
        for country in LOOKUP[match.group(0).casefold()]:
            if country not in found:
                found.append(country)
    if found:
        return found
    # Nothing matched: remaining trips are pastoral visits to Italian towns.
    pieces = re.split(r",|\(|\)|\band\b|\bto\b| - ", re.sub(r"\(.*?\d{4}\)", "", text))
    if any(p.strip().casefold() in ITALIAN_CITIES for p in pieces):
        return ["Italy"]
    return []


def clean_trips(df, drop_italy=True):
    df = df.copy()
    df["Country"] = df["Place"].apply(place_to_countries)

    unresolved = df.loc[df["Country"].str.len() == 0, "Place"]
    if not unresolved.empty:
        print(f"{len(unresolved)} trip(s) without any recognised country, dropped:")
        print(unresolved.to_string())

    df = df.explode("Country").dropna(subset=["Country"])
    if drop_italy:
        df = df.loc[df["Country"] != "Italy"]
    df["ISO3"] = df["Country"].map(NAME_TO_ISO3)
    assert df["ISO3"].notna().all(), df.loc[df["ISO3"].isna(), "Country"].unique()
    return df.reset_index(drop=True)


if __name__ == "__main__":
    fs = s3fs.S3FileSystem(client_kwargs={"endpoint_url": "https://minio.lab.sspcloud.fr"})
    MY_BUCKET = "avibert"
    FILE_PATH_IN = f"{MY_BUCKET}/diffusion/df_trips.parquet"
    FILE_PATH_OUT_Parquet = f"{MY_BUCKET}/diffusion/df_trips_countries.parquet"
    FILE_PATH_OUT_csv = f"{MY_BUCKET}/diffusion/df_trips_countries.csv"

    with fs.open(FILE_PATH_IN, "rb") as file_in:
        df_trips = pd.read_parquet(file_in)

    df_countries = clean_trips(df_trips)
    print(df_countries.head(20))

    with fs.open(FILE_PATH_OUT_Parquet, "wb") as file_out:
        df_countries.to_parquet(file_out)
    with fs.open(FILE_PATH_OUT_csv, "w") as file_out:
        df_countries.to_csv(file_out, index=False)
