"""Rattacher chaque discours à un pays.

Règles, dans l'ordre :
1. Si le titre ou le lieu parle d'un vol ("vol papal", "vol de retour") -> "Avion".
2. On cherche un nom de ville ou de pays (table LIEUX_VERS_PAYS) dans le lieu
   et dans la parenthèse finale du titre, par exemple "(Nairobi, 25 novembre 2015)".
3. Pour un voyage, on cherche ensuite dans la fin du titre (après les deux-points :
   "Voyage apostolique - Kenya : Rencontre avec ..."), puis dans la ligne du voyage
   si elle ne cite qu'un seul pays.
4. Sinon : visite pastorale -> "Italie" ; voyage non résolu -> "Non déterminé" ;
   tout le reste -> "Vatican / Rome" (la grande majorité des discours).

On ne regarde PAS le reste du titre pour les discours au Vatican : "Aux évêques
du Portugal" est un discours prononcé à Rome, pas au Portugal.
"""
import re

# Mot-clé (en minuscules) -> pays. Compléter cette table si un lieu manque.
LIEUX_VERS_PAYS = {
    # Pièges : salles du Vatican qui portent un nom de ville
    "salle bologne": "Vatican / Rome",
    # Piège : le « Centre Bethléem » est un foyer à Bratislava
    "centre bethléem": "Slovaquie",
    # Italie (hors Rome)
    "assise": "Italie", "ariccia": "Italie", "naples": "Italie", "pompéi": "Italie",
    "milan": "Italie", "turin": "Italie", "gênes": "Italie", "florence": "Italie",
    "prato": "Italie", "bologne": "Italie", "cesena": "Italie", "cagliari": "Italie",
    "caserte": "Italie", "cosenza": "Italie", "cassano": "Italie", "lampedusa": "Italie",
    "greccio": "Italie", "loppiano": "Italie", "nomadelfia": "Italie", "carpi": "Italie",
    "mirandola": "Italie", "campobasso": "Italie", "isernia": "Italie", "castelpetroso": "Italie",
    "palerme": "Italie", "venise": "Italie", "vérone": "Italie", "l'aquila": "Italie",
    "pietrelcina": "Italie", "san giovanni rotondo": "Italie", "bari": "Italie", "matera": "Italie",
    "trieste": "Italie",
    # Europe
    "strasbourg": "France", "marseille": "France", "ajaccio": "France", "corse": "France",
    "france": "France",
    "genève": "Suisse", "coe": "Suisse", "suisse": "Suisse",
    "tirana": "Albanie", "albanie": "Albanie",
    "sarajevo": "Bosnie-Herzégovine", "bosnie": "Bosnie-Herzégovine",
    "istanbul": "Turquie", "ankara": "Turquie", "turquie": "Turquie",
    "cracovie": "Pologne", "częstochowa": "Pologne", "auschwitz": "Pologne", "pologne": "Pologne",
    "malmö": "Suède", "lund": "Suède", "suède": "Suède",
    "fátima": "Portugal", "fatima": "Portugal", "lisbonne": "Portugal", "portugal": "Portugal",
    "dublin": "Irlande", "knock": "Irlande", "irlande": "Irlande",
    "vilnius": "Lituanie", "kaunas": "Lituanie", "lituanie": "Lituanie",
    "riga": "Lettonie", "aglona": "Lettonie", "lettonie": "Lettonie",
    "tallinn": "Estonie", "estonie": "Estonie",
    "sofia": "Bulgarie", "rakovski": "Bulgarie", "rakovsky": "Bulgarie", "bulgarie": "Bulgarie",
    "skopje": "Macédoine du Nord", "macédoine": "Macédoine du Nord",
    "bucarest": "Roumanie", "iasi": "Roumanie", "blaj": "Roumanie", "roumanie": "Roumanie",
    "la valette": "Malte", "gozo": "Malte", "malte": "Malte", "malta": "Malte",
    "nicosie": "Chypre", "chypre": "Chypre",
    "athènes": "Grèce", "lesbos": "Grèce", "mytilène": "Grèce", "grèce": "Grèce",
    "budapest": "Hongrie", "hongrie": "Hongrie",
    "bratislava": "Slovaquie", "prešov": "Slovaquie", "košice": "Slovaquie", "šaštin": "Slovaquie",
    "slovaquie": "Slovaquie",
    "luxembourg": "Luxembourg",
    "bruxelles": "Belgique", "louvain": "Belgique", "belgique": "Belgique",
    # Moyen-Orient et Caucase
    "amman": "Jordanie", "jordanie": "Jordanie",
    "bethléem": "Palestine", "palestine": "Palestine",
    "jérusalem": "Israël", "tel aviv": "Israël", "israël": "Israël",
    "le caire": "Égypte", "caire": "Égypte", "égypte": "Égypte",
    "erevan": "Arménie", "yerevan": "Arménie", "etchmiadzin": "Arménie", "gyumri": "Arménie",
    "arménie": "Arménie",
    "tbilissi": "Géorgie", "mtskheta": "Géorgie", "géorgie": "Géorgie",
    "bakou": "Azerbaïdjan", "azerbaïdjan": "Azerbaïdjan",
    "abou dabi": "Émirats arabes unis", "émirats": "Émirats arabes unis",
    "rabat": "Maroc", "maroc": "Maroc",
    "bagdad": "Irak", "erbil": "Irak", "mossoul": "Irak", "qaraqosh": "Irak", "nadjaf": "Irak",
    "irak": "Irak",
    "awali": "Bahreïn", "manama": "Bahreïn", "sakhir": "Bahreïn", "bahreïn": "Bahreïn",
    "noursoultan": "Kazakhstan", "nour-soultan": "Kazakhstan", "astana": "Kazakhstan",
    "kazakhstan": "Kazakhstan",
    # Asie
    "séoul": "Corée du Sud", "solmoe": "Corée du Sud", "haemi": "Corée du Sud",
    "kkottongnae": "Corée du Sud", "daejeon": "Corée du Sud", "corée": "Corée du Sud",
    "colombo": "Sri Lanka", "madhu": "Sri Lanka", "sri lanka": "Sri Lanka",
    "manille": "Philippines", "tacloban": "Philippines", "palo": "Philippines",
    "philippines": "Philippines",
    "yangon": "Myanmar", "nay pyi taw": "Myanmar", "myanmar": "Myanmar", "birmanie": "Myanmar",
    "dhaka": "Bangladesh", "bangladesh": "Bangladesh",
    "bangkok": "Thaïlande", "thaïlande": "Thaïlande",
    "tokyo": "Japon", "nagasaki": "Japon", "hiroshima": "Japon", "japon": "Japon",
    "oulan-bator": "Mongolie", "mongolie": "Mongolie",
    "jakarta": "Indonésie", "indonésie": "Indonésie",
    "port moresby": "Papouasie-Nouvelle-Guinée", "vanimo": "Papouasie-Nouvelle-Guinée",
    "papouasie": "Papouasie-Nouvelle-Guinée",
    "dili": "Timor oriental", "timor": "Timor oriental",
    "singapour": "Singapour",
    # Afrique
    "nairobi": "Kenya", "kenya": "Kenya",
    "kampala": "Ouganda", "entebbe": "Ouganda", "namugongo": "Ouganda", "munyonyo": "Ouganda",
    "ouganda": "Ouganda",
    "bangui": "Centrafrique", "centrafricaine": "Centrafrique",
    "maputo": "Mozambique", "mozambique": "Mozambique",
    "antananarivo": "Madagascar", "madagascar": "Madagascar",
    "port louis": "Maurice", "maurice": "Maurice",
    "kinshasa": "RD Congo", "congo": "RD Congo",
    "djouba": "Soudan du Sud", "juba": "Soudan du Sud", "soudan": "Soudan du Sud",
    # Amériques
    "rio de janeiro": "Brésil", "aparecida": "Brésil", "brésil": "Brésil",
    "quito": "Équateur", "guayaquil": "Équateur", "quinche": "Équateur", "équateur": "Équateur",
    "la paz": "Bolivie", "el alto": "Bolivie", "santa cruz": "Bolivie", "palmasola": "Bolivie",
    "bolivie": "Bolivie",
    "asunción": "Paraguay", "caacupé": "Paraguay", "paraguay": "Paraguay",
    "la havane": "Cuba", "holguín": "Cuba", "santiago de cuba": "Cuba", "cuba": "Cuba",
    "washington": "États-Unis", "new york": "États-Unis", "philadelphie": "États-Unis",
    "onu": "États-Unis", "états-unis": "États-Unis",
    "mexico": "Mexique", "juárez": "Mexique", "morelia": "Mexique", "tuxtla": "Mexique",
    "ecatepec": "Mexique", "chiapas": "Mexique", "mexique": "Mexique",
    "bogota": "Colombie", "bogotá": "Colombie", "medellín": "Colombie",
    "villavicencio": "Colombie", "carthagène": "Colombie", "colombie": "Colombie",
    "santiago": "Chili", "temuco": "Chili", "iquique": "Chili", "hurtado": "Chili", "chili": "Chili",
    "lima": "Pérou", "trujillo": "Pérou", "puerto maldonado": "Pérou", "pérou": "Pérou",
    "panamá": "Panama", "panama": "Panama",
    "edmonton": "Canada", "québec": "Canada", "iqaluit": "Canada", "maskwacis": "Canada",
    "canada": "Canada",
}

# On teste les mots-clés les plus longs d'abord ("santiago de cuba" avant "santiago")
MOTS_CLES_TRIES = sorted(LIEUX_VERS_PAYS, key=len, reverse=True)


def pays_cites(texte):
    """Renvoie la liste des pays (sans doublon) dont un mot-clé apparaît dans le texte."""
    texte = texte.lower()
    pays = []
    for mot_cle in MOTS_CLES_TRIES:
        if re.search(rf"\b{re.escape(mot_cle)}\b", texte):
            if LIEUX_VERS_PAYS[mot_cle] not in pays:
                pays.append(LIEUX_VERS_PAYS[mot_cle])
            texte = texte.replace(mot_cle, " ")  # évite que "santiago" retrouve "santiago de cuba"
    return pays


def parenthese_finale(titre):
    """Renvoie le contenu de la dernière parenthèse du titre : "(Nairobi, 25 novembre 2015)"."""
    resultat = re.search(r"\(([^()]*)\)\s*$", titre)
    return resultat.group(1) if resultat else ""


def pays_du_discours(d):
    """d est un dictionnaire avec les clés "titre", "lieu" et "voyage"."""
    titre, lieu, voyage = d["titre"], d["lieu"], d["voyage"]
    est_un_voyage = voyage.upper().startswith("VOYAGE APOSTOLIQUE")

    # 1. Discours dans l'avion
    if re.search(r"\bvol\b", titre + " " + lieu, re.IGNORECASE):
        return "Avion"

    # 2. Lieu et parenthèse finale du titre
    trouves = pays_cites(lieu + " " + parenthese_finale(titre))
    if trouves:
        return trouves[0]

    if est_un_voyage:
        # 3a. Fin du titre, après les deux-points
        trouves = pays_cites(titre.split(":")[-1])
        if len(trouves) == 1:
            return trouves[0]
        # 3b. Ligne du voyage, si elle ne cite qu'un seul pays
        trouves = pays_cites(voyage)
        if len(trouves) == 1:
            return trouves[0]
        return "Non déterminé"

    # 4. Autres cas
    if voyage.upper().startswith("VISITE PASTORALE"):
        return "Italie"
    return "Vatican / Rome"
