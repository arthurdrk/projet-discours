# Collecter les discours du pape

Python 3.10+ ; Windows, macOS ou Linux. Le périmètre est la rubrique
« speeches » (discours), pas les homélies, audiences ou encycliques.

## Installation

Dans ce dossier, exécuter :

```bash
python -m pip install -r requirements.txt
python -m playwright install chromium
```

Sous Linux, si Chromium signale des bibliothèques système absentes :
`python -m playwright install --with-deps chromium` (peut nécessiter sudo).

## Exemples

Décembre 2025, uniquement les versions françaises :

```bash
python telecharger_discours.py
```

Les deux liens fournis, toutes les traductions proposées :

```bash
python telecharger_discours.py --languages all --urls "https://www.vatican.va/content/leo-xiv/fr/speeches/2025/december.index.html" "https://www.vatican.va/content/leo-xiv/en/speeches/2026/october/documents/20261002-artisti-dce.html"
```

Tous les discours de Léon XIV accessibles depuis l’index, en français :

```bash
python telecharger_discours.py --languages fr --urls "https://www.vatican.va/content/leo-xiv/fr/speeches.index.html"
```

Ajouter `--limit 2` pour un essai, `--output mon_corpus` pour changer le
dossier, ou `--force` pour actualiser les fichiers déjà téléchargés.
Les index annuels sont aussi acceptés, par exemple `.../speeches/2025.index.html`.
Pour un autre pape, fournir son index Vatican correspondant.

## Fichiers produits

Les fichiers sont rangés dans `donnees_vatican/<pape>/<langue>/<année>/`.
Leur nom suit `AAAA-MM-JJ_pape_langue_identifiant_suffixe.pdf`.
Le suffixe déterministe de 10 caractères évite les collisions après troncature.
Chaque PDF est accompagné d’un `.txt` UTF-8 et d’un `.json`.

À la racine :

- `metadata.csv` : index cumulatif des collectes réussies (date, langue, titre,
  URL source, chemins relatifs, SHA-256, méthode PDF, date de collecte UTC).
- `inventaire.json` : versions découvertes lors du dernier lancement et filtre
  de langue appliqué. Le filtre `--limit` intervient ensuite.
- `erreurs.json` : erreurs du dernier lancement, y compris les index inaccessibles.

Les fichiers déjà présents sont réutilisés si les empreintes du PDF et du TXT
correspondent aux métadonnées. `--force` vérifie une éventuelle mise à jour en ligne.
Éviter deux exécutions simultanées dans le même dossier de sortie.

## Langues et complétude

Par défaut, seules les versions françaises sont collectées. Aucun remplacement
par l’anglais n’est effectué silencieusement. `--languages fr en` collecte les
deux langues ; `--languages all` collecte toutes les versions découvertes.
Une URL de discours individuel conserve sa langue et reste soumise au filtre :
pour le lien anglais fourni, utiliser `--languages en` ou `all`.

Un même `speech_id` dans plusieurs langues représente plusieurs traductions du
même discours, à distinguer dans l’analyse. Un corpus français n’est donc pas
nécessairement exhaustif des discours prononcés. Le collecteur dépend des liens
publiés dans les index ; une erreur réseau ou un changement du site peut rendre
la collecte incomplète. Le programme renvoie un code de sortie 1 en cas d’erreurs.

## Comment les PDF sont obtenus

Le programme télécharge un lien `.pdf` lorsqu’il existe. Sinon, il ouvre Chromium
sans fenêtre et clique le bouton `#pdfGenerator` : c’est le PDF généré par le
site lui-même. Il n’invente pas une URL PDF à partir de l’URL HTML.
Les téléchargements intermédiaires utilisent `.part`, puis sont renommés.

Les PDF produits par le bouton du site peuvent être des images. Pour le NLP,
utiliser les fichiers TXT extraits des paragraphes du conteneur `.documento`.
Ce nettoyage léger conserve en-têtes, notes, citations et signatures : il faudra
les traiter selon la question de recherche. Aucune traduction automatique,
lemmatisation ou suppression de mots n’est appliquée.

Les requêtes sont séquentielles, espacées de 1,5 seconde par défaut
(`--delay`), avec nouvelles tentatives HTTP pour les erreurs temporaires.
Les erreurs du navigateur sont consignées et peuvent être reprises en relançant.

## Lecture du corpus (optionnel)

Après `python -m pip install pandas` :

```python
from pathlib import Path
import pandas as pd

root = Path('donnees_vatican')
df = pd.read_csv(root / 'metadata.csv', encoding='utf-8-sig')
df['texte'] = df['text_path'].map(lambda p: (root / p).read_text(encoding='utf-8'))
print(df[['date', 'language', 'title']].head())
```

## Vérifications réalisées

Découverte sur l’index fourni de décembre 2025 : 150 versions, dont 16 françaises.
Téléchargement de bout en bout du PDF anglais du 2 octobre 2026 via le bouton du
site, et extraction TXT réussis avec Playwright 1.55.0. L’environnement de test
nécessitait une exception au certificat de son proxy dans le banc de test
uniquement ; le script livré conserve les vérifications TLS normales.

## Version 2 : tous les papes

```bash
python telecharger_discours.py --all-popes --languages all --output corpus_tous_papes
```

Cette option remplace `--urls`. Elle parcourt les notices de l’annuaire officiel,
repère leurs sites de pontificat, puis les index « speeches » exposés par leur
navigation. Les anciennes URL sans mois et les identifiants historiques
`hf_..._spe_...` sont pris en charge. Les dates YYYYMMDD et DDMMYYYY sont reconnues ;
une date non reconnue reste vide dans le CSV et devient « date-inconnue » dans
le nom du fichier. L’identifiant historique complet est conservé.

Pour inventorier avant de télécharger :

```bash
python telecharger_discours.py --all-popes --languages all --discover-only --output corpus_tous_papes
```

`papes.json` indique, pour chaque notice visitée, les index trouvés et le statut :
`indexes_found`, `no_speeches_index_found` ou `error`. Une absence d’index ne prouve
pas qu’aucun texte de ce pape n’existe ailleurs sur le site. Les anciennes pages
hors de la structure `/content/<pape>/<langue>/speeches/` ne sont pas collectées.
La portée est donc tous les discours découvrables via ces rubriques publiques,
pas une garantie d’exhaustivité de tous les documents historiques du Vatican.

L’inventaire de tous les pontificats peut prendre plusieurs minutes avant le
premier PDF, puis la collecte complète beaucoup plus longtemps. `--limit` limite
les téléchargements, pas l’inventaire. Ne pas lancer deux collectes en parallèle
vers le même dossier. Utiliser de préférence un nouveau dossier pour cette v2 :
les noms conservent désormais l’identifiant historique complet.

La découverte des index a été testée sur Pie XII, Jean-Paul II et Léon XIV ;
les parseurs ont été vérifiés sur des index de 1939, 1978 et 2025. La collecte
intégrale de tous les pontificats n’a pas été exécutée lors de la préparation.
