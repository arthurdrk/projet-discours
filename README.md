# Les discours de François en voyage

Le projet rassemble les **discours en anglais** prononcés par le pape François
**sur place** pendant ses **voyages apostoliques hors d'Italie** (2013–2024),
publiés sur vatican.va. Les discours du Vatican, de Rome et des visites en Italie
sont exclus, comme les conférences de presse dans l'avion. On extrait les textes,
les lieux, les pays et les publics pour les analyser.

## Ouvrir les analyses

Les notebooks chargent les données préparées depuis le stockage S3 du SSPCloud
(adresse publique, aucun identifiant nécessaire) : il n'est pas utile de relancer
la collecte pour les exécuter.

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

## Collecter et préparer les données

À la racine du projet, avec l'environnement Python activé :

```powershell
python acquisition/telecharger_discours.py   # environ 10 minutes -> data/discours_bruts.parquet
python acquisition/preparer_corpus.py        # quelques secondes  -> data/discours.parquet
```

**Collecte** (`acquisition/telecharger_discours.py`). La page de chaque année sur vatican.va
liste les voyages hors d'Italie ; le titre d'un voyage donne ses dates, par exemple
« (30 September - 2 October 2016) ». L'index mensuel des discours (rubrique
*speeches*) donne la date de chaque discours dans son adresse : on garde ceux
prononcés pendant un voyage. Les pages des voyages ne suffisent pas, car après 2016
elles ne renvoient plus directement vers les textes. Le voyage à Dubaï (COP28,
décembre 2023) est écarté : il a été annulé et les discours lus par un autre.

**Préparation** (`acquisition/preparer_corpus.py`). Chaque texte est découpé en un en-tête
(paragraphes centrés : voyage, public, lieu, date) et un corps ; le lieu est lu dans
l'en-tête. Deux cas sont écartés (le script affiche combien) :

- les discours prononcés au Vatican le matin du départ (leur en-tête ne mentionne
  pas le voyage) ;
- les conférences de presse et échanges avec les journalistes, surtout dans
  l'avion : ils ne sont pas prononcés dans le pays et contiennent les questions des
  journalistes.

**Stockage** (`outils/stockage.py`). Les deux scripts écrivent dans `data/` (non
versionné), puis copient les fichiers dans le dossier public
`arthurdk/diffusion/projet-discours/` du S3 du SSPCloud. L'écriture demande les
identifiants S3 du propriétaire du bucket, déjà présents dans un service du
SSPCloud ; sans eux, les fichiers restent dans `data/` et
`python outils/stockage.py` permet de les envoyer plus tard. La lecture passe par
l'adresse publique `https://minio.lab.sspcloud.fr/arthurdk/diffusion/projet-discours/`.

Pour écrire sur le S3 depuis son propre ordinateur, récupérer des identifiants
temporaires sur datalab.sspcloud.fr (*Mon compte → Connexion au stockage*) et les
définir dans le terminal avant de lancer les scripts :

```powershell
$env:AWS_ACCESS_KEY_ID = "..."
$env:AWS_SECRET_ACCESS_KEY = "..."
$env:AWS_SESSION_TOKEN = "..."
```

## Les fichiers utiles

| Fichier ou dossier | Rôle |
| --- | --- |
| `acquisition/telecharger_discours.py` | Collecter les discours des voyages sur vatican.va |
| `acquisition/preparer_corpus.py` | Séparer en-têtes et textes, lire les lieux, écarter les textes hors périmètre |
| `acquisition/scraping_no_speeches.py`, `cleaning_no_speeches.py` | Travail d'Adrien en cours : table des voyages de trois papes, lieux et pays (pas encore utilisé par les notebooks) |
| `outils/stockage.py` | Lire et écrire les données (dossier `data/` et S3 du SSPCloud) |
| `outils/analyse_corpus.py` | Fonctions communes aux notebooks |
| `notebooks/` | Analyser le corpus |
| `analyses_html/` | Copies consultables des notebooks déjà exécutés |
| `resultats/` | Graphiques et tableaux exportés (non versionnés) |
| `docs/` | Notes méthodologiques et ancien inventaire des papes |
| `tests/` | Vérifications de la collecte et de la préparation, sans réseau |

Ne pas modifier les données pour corriger un pays ou un public : compléter
`LIEUX` (villes -> pays) ou `PUBLICS` dans `outils/analyse_corpus.py`. Le notebook
01 liste les discours sans pays attribué et des exemples de titres par public.

Les dossiers cachés `.venv`, `.deps` et `.notebook-runtime` servent à
l'environnement local. Ils ne font pas partie du code à étudier.

## Vérifier le code

```powershell
python -m unittest discover -s tests
```

Les thèmes NMF restent exploratoires : lire les textes représentatifs et
vérifier la stabilité avant de les nommer. Les notebooks expliquent les limites
et les paramètres à modifier.
