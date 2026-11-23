"""Lire et écrire les données du projet : dossier data/ en local, copie sur le S3 du SSPCloud.

Les fichiers sont déposés dans le dossier « diffusion » du bucket d'Arthur (arthurdk). Sur le
SSPCloud, ce dossier est lisible par tous à une simple adresse web : les notebooks
peuvent donc charger les données sans identifiants et sans relancer la collecte.

Écrire sur le S3 demande les identifiants S3 du propriétaire du bucket (variables
AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY et AWS_SESSION_TOKEN, déjà définies dans
un service du SSPCloud). Sans eux, les fichiers restent seulement dans data/.

Envoyer sur le S3 les fichiers déjà présents dans data/ : python outils/stockage.py
"""
from pathlib import Path

import pandas as pd

ENDPOINT = "https://minio.lab.sspcloud.fr"
DOSSIER_S3 = "arthurdk/diffusion/projet-discours"
DOSSIER_LOCAL = Path(__file__).resolve().parents[1] / "data"


def adresse_publique(nom):
    """Adresse web publique d'un fichier du projet sur le S3."""
    return f"{ENDPOINT}/{DOSSIER_S3}/{nom}"


def envoyer_sur_s3(nom):
    """Copier data/<nom> sur le S3. Renvoie True si l'envoi a réussi."""
    try:
        import s3fs
        s3 = s3fs.S3FileSystem(client_kwargs={"endpoint_url": ENDPOINT})
        s3.put(str(DOSSIER_LOCAL / nom), f"{DOSSIER_S3}/{nom}")
    except Exception as erreur:  # identifiants absents ou expirés, pas de droits, pas de réseau
        print(f"  Pas d'envoi sur le S3 pour {nom} : {erreur}")
        return False
    print(f"  Envoyé sur le S3 : {adresse_publique(nom)}")
    return True


def enregistrer(df, nom):
    """Écrire df en parquet dans data/<nom>, puis tenter de le copier sur le S3."""
    DOSSIER_LOCAL.mkdir(exist_ok=True)
    df.to_parquet(DOSSIER_LOCAL / nom, index=False)
    print(f"  Enregistré : data/{nom} ({len(df)} lignes)")
    envoyer_sur_s3(nom)


def lire(nom):
    """Lire data/<nom> s'il existe, sinon la version publique sur le S3."""
    chemin = DOSSIER_LOCAL / nom
    if chemin.exists():
        return pd.read_parquet(chemin)
    try:
        return pd.read_parquet(adresse_publique(nom))
    except Exception as erreur:
        raise FileNotFoundError(
            f"{nom} est absent de data/ et du S3 ({adresse_publique(nom)}). "
            "Lancer python telecharger_discours.py puis python preparer_corpus.py."
        ) from erreur


if __name__ == "__main__":
    for fichier in sorted(DOSSIER_LOCAL.glob("*.parquet")):
        envoyer_sur_s3(fichier.name)
