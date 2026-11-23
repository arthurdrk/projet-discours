# Les discours du pape François en voyage

Ce projet étudie les discours prononcés par le pape François pendant ses voyages hors d'Italie, de 2013 à 2024. La question est la suivante : adapte-t-il ce qu'il dit au pays et au public qu'il rencontre ?

Le rapport est le notebook `notebooks/rapport.ipynb`.

## Lancer le rapport

```bash
python -m pip install -r requirements.txt
jupyter lab notebooks/rapport.ipynb
```

Le notebook charge les données préparées depuis le stockage du SSP Cloud, à l'adresse publique https://minio.lab.sspcloud.fr/arthurdk/diffusion/projet-discours/. Il n'est pas nécessaire de relancer la collecte.

## Refaire la collecte

Les données viennent du site vatican.va. Depuis la racine du projet :

```bash
python acquisition/telecharger_discours.py   # une dizaine de minutes, produit data/discours_bruts.parquet
python acquisition/preparer_corpus.py        # quelques secondes, produit data/discours.parquet
```

Le premier script lit les dates de chaque voyage hors d'Italie, puis garde dans les index mensuels les discours prononcés à ces dates (415 textes). Le second sépare l'en-tête du discours, lit le lieu et retire les conférences de presse dans l'avion ainsi que deux discours prononcés au Vatican le matin d'un départ (342 discours).

Les fichiers sont écrits dans `data/`, puis copiés sur le SSP Cloud si les identifiants S3 sont définis. Dans un service du SSP Cloud, ils le sont déjà. Sur un autre ordinateur, il faut définir `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` et `AWS_SESSION_TOKEN`, que l'on trouve dans Mon compte, rubrique Connexion au stockage.

## Organisation du dépôt

| Dossier | Contenu |
| --- | --- |
| `notebooks/` | Le rapport |
| `acquisition/` | Collecte et préparation des discours. Les scripts `scraping_no_speeches.py` et `cleaning_no_speeches.py` construisent une table des voyages des trois derniers papes et ne servent pas au rapport. |
| `outils/` | Fonctions communes : lecture et écriture des données, analyse, graphiques |
| `tests/` | Tests de la collecte et de la préparation, sans accès au réseau |
| `docs/` | Notes de travail |

Pour lancer les tests : `python -m unittest discover -s tests`
