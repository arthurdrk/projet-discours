# Le pape François en voyage : où il va et ce qu'il dit

Ce projet étudie les voyages du pape François hors d'Italie, de 2013 à 2024, et les discours qu'il y a prononcés. Il pose deux questions. Où va le pape, par rapport à ses deux prédécesseurs ? Adapte-t-il ce qu'il dit au pays et au public qu'il rencontre ?

Le rapport est un seul notebook, en anglais : `main.ipynb`, à la racine du dépôt. Il a trois parties : les pays visités par les trois derniers papes (Adrien), l'analyse des 342 discours de François, dont les thèmes par pays (Quentin et Arthur), et la robustesse des écarts, par bootstrap et régression binomiale négative (Quentin). Toutes les analyses des discours utilisent le même corpus, et toutes celles des voyages la table d'Adrien, produits par les scripts du dossier `acquisition/`. Sa version web, avec des graphiques interactifs, est en ligne sur https://arthurdrk.github.io/projet-discours/.

## Lancer le rapport

```bash
python -m pip install -r requirements.txt
jupyter lab main.ipynb
```

Le notebook charge les données préparées depuis le stockage du SSP Cloud, sans identifiant. Il n'est pas nécessaire de relancer la collecte. Les discours (`discours.parquet`) sont dans https://minio.lab.sspcloud.fr/arthurdk/diffusion/projet-discours/. La table des voyages des trois papes (`df_trips_countries.parquet`), les données RCS-Dem 2.0 sur les religions (fichier SPSS) et le PIB par habitant de la Banque mondiale (deux fichiers csv) sont dans le dossier public d'Adrien, https://minio.lab.sspcloud.fr/avibert/diffusion/. Un fichier absent de `data/` y est copié la première fois qu'on en a besoin.

## Le site

Le site est construit avec Quarto à partir du notebook, sans le réexécuter. Une GitHub Action le publie à chaque push sur `main` (`.github/workflows/site.yml`). Pour le voir en local : `quarto preview`.

## Refaire la collecte

Les discours viennent du site vatican.va. Depuis la racine du projet :

```bash
python acquisition/telecharger_discours.py   # une dizaine de minutes, produit data/discours_bruts.parquet
python acquisition/preparer_corpus.py        # quelques secondes, produit data/discours.parquet
```

Le premier script lit les dates de chaque voyage hors d'Italie, puis garde dans les index mensuels les discours prononcés à ces dates (415 textes). Le second sépare l'en-tête du discours, lit le lieu et retire les conférences de presse dans l'avion ainsi que deux discours prononcés au Vatican le matin d'un départ (342 discours).

Les fichiers sont écrits dans `data/`, puis copiés sur le SSP Cloud si les identifiants S3 sont définis. Dans un service du SSP Cloud, ils le sont déjà. Sur un autre ordinateur, il faut définir `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` et `AWS_SESSION_TOKEN`, que l'on trouve dans Mon compte, rubrique Connexion au stockage.

La table des voyages des trois papes vient aussi de vatican.va :

```bash
python acquisition/scraping_no_speeches.py   # liste des voyages, produit df_trips.parquet
python acquisition/cleaning_no_speeches.py   # pays visités et code ISO3, produit df_trips_countries.parquet
```

Ces deux scripts lisent et écrivent dans le dossier `avibert/diffusion` du SSP Cloud, avec les identifiants S3 d'Adrien. Les fichiers RCS-Dem 2.0 (religions) et Banque mondiale (PIB par habitant, https://data.worldbank.org/indicator/NY.GDP.PCAP.KD) se téléchargent à la main sur le site de leur producteur. Le notebook corrige deux points de la table des voyages : il ajoute le Luxembourg et la Belgique au voyage de Jean-Paul II de 1985, et retire le voyage de François à Dubaï pour la COP28, annulé.

## Organisation du dépôt

| Dossier | Contenu |
| --- | --- |
| `main.ipynb` | Le rapport |
| `index.qmd`, `_quarto.yml`, `site.css` | Le site web du rapport |
| `acquisition/` | Collecte et préparation des discours (`telecharger_discours.py`, `preparer_corpus.py`) et des voyages des trois derniers papes (`scraping_no_speeches.py`, `cleaning_no_speeches.py`). `archives_cleaning_spacy.py` est une ancienne version du nettoyage des voyages, gardée pour mémoire et non utilisée. |
| `outils/` | Fonctions communes : lecture et écriture des données, analyse des discours, robustesse (bootstrap et régression), noms anglais des catégories, graphiques |
| `docs/` | Notes de travail |
