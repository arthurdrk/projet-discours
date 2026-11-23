# Notes de travail

## Sources

- Voyages hors d'Italie : https://www.vatican.va/content/francesco/en/travels.index.html (une page par année, `travels/<année>/outside.index.html`)
- Discours : https://www.vatican.va/content/francesco/en/speeches.index.html

Le corpus contient les discours en anglais des voyages apostoliques hors d'Italie de 2013 à 2024. Le voyage à Dubaï de 2023, annulé, est écarté. Un discours est retenu si sa date tombe pendant un voyage et si son en-tête mentionne le voyage. Les conférences de presse et les échanges avec les journalistes sont écartés (voir `acquisition/preparer_corpus.py`). Les homélies ne sont pas incluses.

## Distinguer les lieux

Le pays du discours, le public et les pays évoqués dans le texte sont trois informations différentes. Le pays vient de l'en-tête (lieu), du voyage quand il ne compte qu'un pays, ou des autres discours du même jour.

## Pistes

- François adapte-t-il ses thèmes au continent et au public ?
- Nomme-t-il le pays hôte, et de quels autres pays parle-t-il depuis l'étranger ?
- Quels prédécesseurs et quels textes cite-t-il en voyage ?
- Comment diffèrent les discours aux autorités, aux évêques et aux jeunes ?

## Limites

Un discours peut avoir été remis par écrit plutôt que prononcé. Les traductions anglaises sont celles du Vatican, alors que le pape parlait souvent espagnol ou italien. Une différence entre continents peut venir du public ou de l'actualité du voyage, sans effet propre du lieu.
