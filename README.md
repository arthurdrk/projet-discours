# Discours du pape François

Le projet contient 33 discours français de septembre 2015. On conserve les
pages originales, puis on extrait les textes et les lieux pour les analyser.

## Ouvrir les analyses

Double-cliquer sur **OUVRIR_NOTEBOOKS.cmd**, puis ouvrir les notebooks dans l'ordre :

1. `01_exploration_corpus.ipynb` : qualité, dates, longueurs et recherche de mots.
2. `02_lieux_et_geographie.ipynb` : lieux, corrections manuelles et graphiques.
3. `03_themes_et_lieux.ipynb` : thèmes et comparaison entre lieux.

Les versions dans `analyses_html/` se lisent aussi directement dans un navigateur.

## Installer sur une autre machine

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Télécharger et préparer

À la racine du projet, avec l'environnement Python activé :

```powershell
# Tous les discours disponibles en français, année par année (2013–2025)
python telecharger_discours.py

# Produire les données utilisées par les notebooks après la collecte
python preparer_corpus.py
```

Pour vérifier le périmètre ou faire un essai :

```powershell
# Inventorier toutes les années sans télécharger les textes
python telecharger_discours.py --discover-only

# Télécharger seulement certaines années
python telecharger_discours.py --years 2013 2014

# Essai : les 10 premiers textes de septembre 2015
python telecharger_discours.py --url https://www.vatican.va/content/francesco/fr/speeches/2015/september.index.html --limit 10
```

Sans `--url`, le collecteur parcourt explicitement chaque index annuel de 2013
à 2025, puis ses mois. Il télécharge une année avant de passer à la suivante.
La collecte complète peut prendre plusieurs heures. `--limit` limite le nombre
de textes traités (fichiers déjà présents inclus) et arrête ensuite la collecte.

On peut interrompre avec Ctrl+C, puis relancer la même commande : les HTML et
TXT déjà téléchargés sont vérifiés par leurs empreintes et réutilisés. Les erreurs
HTTP temporaires sont réessayées trois fois. Garder une seule collecte active
dans le même dossier de sortie.

`bilan_collecte.json` suit chaque année : nombre de textes découverts (`found`),
réussis ou réutilisés (`success`), et statut (`complete`, `incomplete`, `limited`,
`interrupted` ou `inventoried` pour un simple inventaire). Le bilan et
`inventaire.json` concernent le lancement courant ; les sources déjà collectées
restent dans leurs dossiers. Un index vide est signalé comme une erreur.

Pour une autre langue ou un autre pape, changer l'URL et éventuellement le
répertoire avec `--output`. Le collecteur suit uniquement la langue de l'URL.
Les fichiers déjà présents sont réutilisés ; `--force` les actualise.
Les erreurs sont enregistrées dans `corpus_francois/erreurs.json`.
Le programme renvoie 1 en cas d'erreur et 130 après une interruption.
Relancer `preparer_corpus.py` après une collecte pour actualiser les notebooks.

« Tout le corpus » désigne ici la rubrique **Discours** et ses versions françaises
accessibles depuis les index. Les homélies, audiences et encycliques appartiennent
à d'autres rubriques ; certains discours peuvent ne pas avoir de traduction française.

## Les fichiers utiles

| Fichier ou dossier | Rôle |
| --- | --- |
| `telecharger_discours.py` | Télécharger les HTML, TXT et métadonnées |
| `preparer_corpus.py` | Séparer les en-têtes, extraire les lieux et produire le JSONL |
| `notebooks/` | Analyser le corpus |
| `corpus_francois/` | Sources et données préparées |
| `annotations_lieux.csv` | Corrections manuelles des lieux |
| `resultats/` | Graphiques et tableaux exportés |
| `analyses_html/` | Copies consultables des notebooks déjà exécutés |
| `docs/` | Notes méthodologiques et ancien inventaire des papes |
| `outils/` | Lancement Jupyter et exécution automatique des notebooks |
| `tests/` | Vérifications du téléchargement et de l'extraction |

Ne pas modifier les données sources pour corriger un lieu : remplir
`ville_validee` et `statut=valide` dans `annotations_lieux.csv`, puis relancer
les notebooks 02 et 03. Les lieux non validés restent des suggestions.

Les dossiers cachés `.venv`, `.deps` et `.notebook-runtime` servent à
l'environnement local existant. Ils ne font pas partie du code à étudier.

## Vérifier le code

```powershell
python -m unittest discover -s tests
```

Les résultats thématiques restent exploratoires sur ce petit corpus. Les
notebooks expliquent les limites et les paramètres à modifier.
