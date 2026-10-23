import re
import time

import requests
from bs4 import BeautifulSoup

Domain = "https://www.vatican.va"
URL_Base = "https://www.vatican.va/content/vatican/en/holy-father/{pope}.html"

POPES = {"John-Paul II": "giovanni-paolo-ii",
         "Benedict XVI": "benedetto-xvi",
         "Francis": "francesco"
         }


def get_page_years(id_pope, url_base=URL_Base):
    request_page = requests.get(url_base.format(pope=id_pope)).content
    return BeautifulSoup(request_page, features="html.parser")


def get_years(page):
    return_list = []
    for a in page.find_all("a", href=True):
        if "outside Italy" in a.get_text(strip=True):
            return_list.append(Domain + a.get("href"))
    return return_list


def get_trips(url_year):
    return_list = []
    request_page = requests.get(url_year).content
    page = BeautifulSoup(request_page, features="html.parser")
    for div in page.find_all("div", {"class": "item"}):
        for h2 in div.find_all("h2"):
            for a in h2.find_all("a", href=True):
                return_list.append(a.get_text(strip=True))
    return return_list


def extract_place(title):
    m = re.search(r"of the Holy Father to (.*?)\s*\([^()]*\d{4}\)\s*$",
                  title, re.IGNORECASE)
    if not m:
        return None
    texte = re.split(r" and (?:a )?[Vv]isit to ", m.group(1))[0]
    lieux = []
    for morceau in re.split(r",\s*|\s+and\s+", texte):
        morceau = re.sub(r"^the ", "", morceau.strip(), flags=re.IGNORECASE)
        if morceau:
            lieux.append(morceau)
    return lieux


def df_preparation(popes=POPES):
    pre_df = {"Pope": [], "Year": [], "Place": []}
    for Pope_usual, Pope_id in popes.items():
        for year_url in get_years(get_page_years(Pope_id)):
            time.sleep(1)
            for trip in get_trips(year_url):
                pre_df["Pope"].append(Pope_usual)
                pre_df["Year"].append(int(year_url.split("/")[-2]))
                pre_df["Place"].append(trip)
    return pre_df
