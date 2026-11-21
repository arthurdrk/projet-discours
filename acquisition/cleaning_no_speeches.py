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

city_index = defaultdict(list)
for city in gc.get_cities().values():
    for name in {city["name"], *city["alternatenames"]}:
        if name:
            city_index[name.casefold()].append(city)


def get_nlp():
    global nlp
    if nlp is None:
        nlp = spacy.load("en_core_web_sm")
    return nlp


def place_extract(text):
    treated_text = nlp(text)
    places = []
    for entity in treated_text.ents:
        if entity.label_ == "GPE" and entity.text not in places:
            places.append(re.sub(r"[Tt]he\s+", "", entity.text))
    return places


def city_to_country(locality_name):
    results = city_index.get(locality_name.casefold())
    if not results:
        return locality_name
    best = max(results, key=lambda c: c["population"])
    return countries[best["countrycode"]]["name"]


MY_BUCKET = "avibert"
FILE_PATH_OUT_S3_Parquet = f"{MY_BUCKET}/diffusion/df_trips.parquet"

with fs.open(FILE_PATH_OUT_S3_Parquet, 'rb') as file_in:
    df = pd.read_parquet(file_in)

#df["Place_extracted"] = place_extract(df_trips["Place"])
print(df["Place"].isna().sum())
df.head(5)
