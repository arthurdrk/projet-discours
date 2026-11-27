"""ARCHIVE - first version of the cleaning of the papal trips, kept for reference only.

This script is no longer used. It has been replaced by `cleaning_no_speeches.py`
(same folder), which produces avibert/diffusion/df_trips_countries.parquet.

This version relied on spaCy named entity recognition and on geonamescache to find
the countries in the "Place" strings of the trips. It was not reliable enough:
spaCy missed or misclassified many places (cities, shrines, regions given without
their country), and the names used on the Vatican website often differ from the
geonamescache names (historical names such as Zaire or the Federal Republic of
Germany, alternative spellings...).

The new version, written with the help of AI, drops spaCy and uses an explicit
table of aliases that maps every name found on the Vatican website to its country,
which solves both problems.
"""

import re
from collections import defaultdict

import geonamescache
import pandas as pd
import s3fs
import spacy

fs = s3fs.S3FileSystem(client_kwargs={"endpoint_url": "https://minio.lab.sspcloud.fr"})
nlp = None

gc = geonamescache.GeonamesCache()
countries = gc.get_countries()
countries_name = {country["name"] for country in countries.values()}
print(len(countries_name))

city_index = defaultdict(list)
for city in gc.get_cities().values():
    for name in {city["name"], *city["alternatenames"]}:
        if name:
            city_index[name.casefold()].append(city)


def get_nlp():
    global nlp
    if nlp is None:
        nlp = spacy.load("en_core_web_lg")
        ruler = nlp.add_pipe("entity_ruler", before="ner")
        typed_places = ["Holy Land", "Ajaccio", "European Parliament", "Fátima"]
        ruler.add_patterns([{"label": "GPE", "pattern": place} for place in typed_places])
    return nlp


def place_extract(text):
    treated_text = nlp(text)
    places = []
    for entity in treated_text.ents:
        if entity.label_ == "GPE" and entity.text not in places:
            places.append(re.sub(r"[Tt]he\s+", "", entity.text))
    return places


def city_to_country(locality_name):
    if locality_name in countries_name:
        return locality_name
    results = city_index.get(locality_name.casefold())
    print(results)
    if not results:
        return locality_name
    best = max(results, key=lambda c: c["population"])
    return countries[best["countrycode"]]["name"]

if __name__ == "__main__":

    MY_BUCKET = "avibert"
    FILE_PATH_OUT_S3_Parquet = f"{MY_BUCKET}/diffusion/df_trips.parquet"

    with fs.open(FILE_PATH_OUT_S3_Parquet, 'rb') as file_in:
        df = pd.read_parquet(file_in)

    get_nlp()
    df["Place_extracted"] = df["Place"].apply(place_extract)
    df = df.explode("Place_extracted")
    df = df.dropna()
    df["Place_extracted"] = df["Place_extracted"].apply(city_to_country)
    df["Place_extracted"] = df["Place_extracted"].replace(["European Parliament", "Holy Land", "Veneto", "Federal Replublic of Germany"],
                                                        ["France", "Israel", "Italy", "Germany"])
    df = df.loc[df["Place_extracted"] != "Italy", :]
    print(df.loc[~df["Place_extracted"].isin(countries_name), :])