# Les discours de François en voyage

Le projet rassemble les **discours en anglais** prononcés par le pape François
pendant ses **48 voyages apostoliques hors d'Italie** (2013–2024), publiés sur
vatican.va. Les discours du Vatican, de Rome et des visites en Italie sont exclus.
On conserve les pages originales, puis on extrait les textes, les lieux, les pays
et les publics pour les analyser.

## Ouvrir les analyses

Lancer `python outils/lancer_notebooks.py`, puis ouvrir les notebooks dans l'ordre :

1. `01_exploration_corpus.ipynb` : discours par voyage, par année et continent,
   types de public, longueurs, contrôle qualité, suivi d'un mot avec extraits.
2. `02_lieux_et_geographie.ipynb` : cartes des pays visités et des pays mentionnés,
   chronologie des séjours, place du pays hôte, croisement des continents.
3. `03_themes.ipynb` : thèmes NMF, sur-représentation par continent et par public,
   évolution, discours représentatifs, test de stabilité, discours proches.
4. `04_vocabulaire_et_evolution.ipynb` : 16 thèmes définis par des listes de mots,
   comparés par continent, public et année ; mots caractéristiques (log-odds) ;
   références citées ; longueur des phrases.

Les fonctions communes (pays, lieux, publics, lexiques, palette) sont dans
`outils/analyse_corpus.py` : c'est là qu'on modifie un lexique ou une règle.
`python outils/executer_notebooks.py` réexécute tous les notebooks et met à jour
`analyses_html/`.

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
# Discours en anglais des voyages hors d'Italie -> corpus_voyages_en/
python telecharger_discours.py

# Produire les données utilisées par les notebooks
python preparer_corpus.py
```

Comment les discours sont choisis : le collecteur lit la liste des voyages
« hors d'Italie » (`travels/<année>/outside`), prend les dates de chaque voyage
dans son titre, puis parcourt les index mensuels des discours pour ces dates.
Il ne garde que les discours dont l'en-tête mentionne le voyage (« Apostolic
Journey », « Pilgrimage »…) ; les autres sont listés dans `exclus.json`. Chaque
métadonnée JSON indique le voyage (`travel_title`, `travel_start`, `travel_end`).

Autres options :

```powershell
# Inventorier sans télécharger
python telecharger_discours.py --discover-only

# Ajouter les homélies des voyages, ou changer de langue
python telecharger_discours.py --types speeches homilies
python telecharger_discours.py --langue fr

# Rubriques complètes (tous lieux) : speeches, homilies, angelus, audiences,
# cotidie, messages, letters, encyclicals, apost_exhortations, ...
python telecharger_discours.py --perimetre tout --langue fr --types speeches
```

Le dossier de sortie par défaut est `corpus_<perimetre>_<langue>` (par exemple
`corpus_voyages_en`) ; `--output` le change. `--years` filtre par année et
`--limit` arrête après un nombre de textes.

On peut interrompre avec Ctrl+C, puis relancer la même commande : les HTML et
TXT déjà téléchargés sont vérifiés par leurs empreintes et réutilisés. Les erreurs
HTTP temporaires sont réessayées trois fois. Garder une seule collecte active
dans le même dossier de sortie.

`bilan_collecte.json` suit chaque rubrique : nombre de textes découverts (`found`),
réussis ou réutilisés (`success`), et statut (`complete`, `incomplete`, `limited`,
`interrupted` ou `inventoried` pour un simple inventaire). Le bilan et
`inventaire.json` concernent le lancement courant ; les sources déjà collectées
restent dans leurs dossiers. Un index vide est signalé comme une erreur.

Pour une autre langue ou un autre pape, changer l'URL et éventuellement le
répertoire avec `--output`. Le collecteur suit uniquement la langue de l'URL.
Les fichiers déjà présents sont réutilisés ; `--force` les actualise.
Les erreurs sont enregistrées dans `erreurs.json` du dossier de sortie.
Le programme renvoie 1 en cas d'erreur et 130 après une interruption.
Relancer `preparer_corpus.py` après une collecte pour actualiser les notebooks.

Un discours sans version anglaise n'est pas collecté. L'ancien corpus français
(`corpus_francois/`) reste sur le disque mais n'est plus utilisé par les notebooks.

## Les fichiers utiles

| Fichier ou dossier | Rôle |
| --- | --- |
| `telecharger_discours.py` | Télécharger les HTML, TXT et métadonnées |
| `preparer_corpus.py` | Séparer les en-têtes, extraire les lieux et produire le JSONL |
| `notebooks/` | Analyser le corpus |
| `corpus_voyages_en/` | Sources et données préparées |
| `resultats/` | Graphiques et tableaux exportés |
| `analyses_html/` | Copies consultables des notebooks déjà exécutés |
| `docs/` | Notes méthodologiques et ancien inventaire des papes |
| `outils/` | Lancement Jupyter et exécution automatique des notebooks |
| `tests/` | Vérifications du téléchargement et de l'extraction |

Ne pas modifier les données sources pour corriger un pays ou un public : compléter
`LIEUX` (villes -> pays) ou `PUBLICS` dans `outils/analyse_corpus.py`. Le notebook
01 liste les discours sans pays attribué et des exemples de titres par public.

Les dossiers cachés `.venv`, `.deps` et `.notebook-runtime` servent à
l'environnement local existant. Ils ne font pas partie du code à étudier.

## Vérifier le code

```powershell
python -m unittest discover -s tests
```

Les thèmes NMF restent exploratoires : lire les textes représentatifs et
vérifier la stabilité avant de les nommer. Les notebooks expliquent les limites
et les paramètres à modifier.
