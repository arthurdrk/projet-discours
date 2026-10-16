# Notes pour l'analyse

## Sources

- Index : https://www.vatican.va/content/francesco/fr/speeches.index.html
- Pilote : https://www.vatican.va/content/francesco/fr/speeches/2015/september.index.html
- Voyages : https://www.vatican.va/content/francesco/fr/travels/2015/outside.index.html

Le pilote contient 33 textes français, 30 lieux candidats et 3 lieux inconnus.
Les inconnus concernent des échanges en avion. Les autres genres (homélies,
encycliques, audiences) ne sont pas inclus dans la collecte.

## Distinguer les lieux

Le lieu du discours, l'origine du public et les lieux évoqués dans le texte
sont trois informations différentes. L'extraction utilise l'en-tête comme
preuve, sans attribuer automatiquement au discours les pays mentionnés.
Les suggestions de villes dans les notebooks doivent être vérifiées.

## Questions intéressantes

- Comment les thèmes varient-ils selon le lieu et le public ?
- Comment évoluent écologie, pauvreté, migrations et paix au cours du pontificat ?
- Quels pays sont évoqués depuis quels lieux ?
- Quels prédécesseurs et textes sont cités ?
- Comment diffèrent discours préparés et réponses aux journalistes ?

## Limites

Un mois ne représente pas tout le pontificat. Les traductions d'un même
texte ne sont pas des observations indépendantes. Un texte publié peut avoir
été remis par écrit ; le lieu indiqué n'atteste pas une prise de parole.
Les questions des journalistes et les citations peuvent rester dans le corps.

Le notebook thématique utilise TF-IDF et NMF. Lire les documents représentatifs
avant de nommer les thèmes ; comparer plusieurs nombres de thèmes. Les poids
ne sont pas des probabilités. Une différence entre villes peut s'expliquer
par le public, le genre ou la date, sans effet causal du lieu.

## Périmètre du code simplifié

La collecte garde HTML, TXT et métadonnées ; la préparation produit
`corpus_nlp.jsonl`. Le téléchargement PDF et la découverte automatique de tous
les papes ont été retirés. Un autre pape reste accessible via son URL d'index.
L'ancien inventaire `papes.json` est conservé ici pour référence.
