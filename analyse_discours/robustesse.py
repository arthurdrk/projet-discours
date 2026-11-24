"""Les écarts entre pays sont-ils solides ?

LA DÉMARCHE, EN QUATRE TEMPS
============================

1. La question
   Sur le globe, chaque pays a un « indice » par thème :

       indice = (fréquence des mots du thème dans le pays) / (fréquence dans tout le corpus)

   Un indice de 3 pour « paix et guerre » en Irak veut dire que le pape y emploie
   trois fois plus les mots de la paix et de la guerre que d'habitude. Mais peut-on
   vraiment s'y fier ?

2. Premier doute : le hasard. Réponse : le BOOTSTRAP.
   Beaucoup de pays n'ont que 3 à 7 discours. Un seul discours très centré sur un
   thème suffit à faire grimper l'indice. Pour mesurer cette fragilité, on
   « rejoue » le voyage 1 000 fois : à chaque fois, on tire au hasard, avec remise,
   autant de discours que le pays en a (certains reviennent deux fois, d'autres
   disparaissent), et on recalcule l'indice. On garde les 95 % du milieu des
   1 000 valeurs : c'est l'intervalle de confiance.
     - intervalle entièrement au-dessus de 1 -> il en parle vraiment PLUS ici ;
     - entièrement en dessous de 1           -> il en parle vraiment MOINS ;
     - l'intervalle contient 1               -> on ne peut pas conclure.

3. Second doute : les facteurs de confusion. Réponse : la RÉGRESSION.
   En voyage, le pape parle souvent aux autorités ; au Vatican, souvent au clergé.
   Si la paix ressort en Afrique, est-ce l'Afrique ou le public ? Pour séparer
   les deux, on explique le nombre de mots du thème dans chaque discours par la
   région, le public et l'année en même temps (régression binomiale négative,
   une par thème). Chaque coefficient se lit alors « toutes choses égales par
   ailleurs » : ×2 pour « région : Afrique » veut dire deux fois plus de mots du
   thème qu'au Vatican, devant le même type de public et la même année.
     - Binomiale négative plutôt que Poisson : les comptages sont très dispersés
       (beaucoup de discours à 0, quelques-uns à 50), ce que Poisson n'autorise pas.
     - La longueur du discours entre en « offset » : on modélise un taux par mot,
       exactement comme l'indice.

4. Ce qu'on en retient
   On ne garde sur le globe que ce qui résiste : l'intervalle du pays (fiche pays)
   et les effets significatifs de la région et du public (fiche thème). Ce sont des
   corrélations, pas des causes : le programme d'un voyage dépend du pays visité.

Pour voir la démarche déroulée sur un exemple réel, avec les vrais chiffres :
    python analyse_discours/robustesse.py
ou dans le notebook :
    from robustesse import expliquer_demarche
    expliquer_demarche(discours, theme="paix et guerre", pays="Irak")

Autres fonctions utiles dans le notebook :
    intervalles_bootstrap(THEMES["migrations"], discours)     # un thème, tous les pays
    tableau = tableau_par_discours(discours)
    resultat, coefficients = regression_theme("migrations", tableau)
    resume_regressions(tableau)                                # tous les thèmes

Nécessite le paquet statsmodels (pip install statsmodels).
"""
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

from compter_mots import DOSSIER_RESULTATS
from themes import THEMES


# ======================================================================
# 1. L'indice et son intervalle de confiance (bootstrap)
# ======================================================================

def occurrences_du_theme(d, mots):
    """Combien de fois les mots du thème apparaissent dans un discours."""
    return sum(d["compte_mots"][m.lower()] for m in mots)


def frequence_dans_le_corpus(mots, discours):
    """Fréquence des mots du thème dans tout le corpus : c'est le « 1 » de l'indice."""
    total_occurrences = sum(occurrences_du_theme(d, mots) for d in discours)
    total_mots = sum(d["nb_mots"] for d in discours)
    return total_occurrences / total_mots


def ranger_par_lieu(discours, cle="pays"):
    """Regroupe les discours par pays (ou par ville avec cle="ville")."""
    discours_par_lieu = {}
    for d in discours:
        if d["nb_mots"] == 0 or d[cle] is None:   # discours vide ou ville inconnue
            continue
        discours_par_lieu.setdefault(d[cle], []).append(d)
    return discours_par_lieu


def intervalles_bootstrap(mots, discours, n_tirages=1000, niveau=0.95, graine=0, minimum=3,
                          cle="pays"):
    """L'indice du thème dans chaque pays, avec son intervalle de confiance.

    Renvoie un DataFrame : pays, discours, indice, ic_bas, ic_haut, conclusion.
    En dessous de `minimum` discours, on ne calcule pas d'intervalle : il n'y a
    pas assez de matière pour que le tirage au hasard ait un sens.
    Avec cle="ville", le même calcul est fait ville par ville.
    """
    # La graine fixe le hasard : on retrouve exactement les mêmes résultats à chaque lancement
    hasard = np.random.default_rng(graine)
    frequence_globale = frequence_dans_le_corpus(mots, discours)
    part_exclue = (1 - niveau) / 2       # 2,5 % de chaque côté pour un intervalle à 95 %

    lignes = []
    for lieu, liste in ranger_par_lieu(discours, cle).items():
        occurrences = np.array([occurrences_du_theme(d, mots) for d in liste])
        nb_mots = np.array([d["nb_mots"] for d in liste])
        indice = occurrences.sum() / nb_mots.sum() / frequence_globale
        n = len(liste)

        if n < minimum:
            ic_bas, ic_haut = np.nan, np.nan
            conclusion = f"trop peu de discours (< {minimum})"
        else:
            # On « rejoue » le pays n_tirages fois. Chaque ligne de `tirages` contient
            # les numéros des n discours tirés au hasard, avec remise.
            tirages = hasard.integers(0, n, size=(n_tirages, n))
            indices_simules = (occurrences[tirages].sum(axis=1)
                               / nb_mots[tirages].sum(axis=1)
                               / frequence_globale)
            # On garde les 95 % du milieu des indices simulés
            ic_bas, ic_haut = np.quantile(indices_simules, [part_exclue, 1 - part_exclue])

            if ic_bas > 1:
                conclusion = "plus que la moyenne"
            elif ic_haut < 1:
                conclusion = "moins que la moyenne"
            else:
                conclusion = "pas d'écart significatif"

        lignes.append({cle: lieu, "discours": n, "indice": round(indice, 2),
                       "ic_bas": round(ic_bas, 2), "ic_haut": round(ic_haut, 2),
                       "conclusion": conclusion})

    tableau = pd.DataFrame(lignes)
    return tableau.sort_values("indice", ascending=False, ignore_index=True)


def bootstrap_tous_les_themes(discours, **options):
    """Le même calcul pour les 12 thèmes, empilés dans un seul tableau."""
    tableaux = []
    for theme, mots in THEMES.items():
        tableau = intervalles_bootstrap(mots, discours, **options)
        tableau.insert(0, "theme", theme)
        tableaux.append(tableau)
    return pd.concat(tableaux, ignore_index=True)


# ======================================================================
# 2. Les variables de la régression : région, public, année
# ======================================================================

# On regroupe les pays en grandes régions : un pays seul a trop peu de
# discours pour avoir son propre coefficient.
REGIONS = {
    "Europe": [
        "France", "Suisse", "Albanie", "Bosnie-Herzégovine", "Pologne", "Suède",
        "Portugal", "Irlande", "Lituanie", "Lettonie", "Estonie", "Bulgarie",
        "Macédoine du Nord", "Roumanie", "Malte", "Chypre", "Grèce", "Hongrie",
        "Slovaquie", "Luxembourg", "Belgique",
    ],
    "Moyen-Orient et Caucase": [
        "Turquie", "Jordanie", "Palestine", "Israël", "Arménie", "Géorgie",
        "Azerbaïdjan", "Émirats arabes unis", "Irak", "Bahreïn",
    ],
    "Afrique": [
        "Égypte", "Maroc", "Kenya", "Ouganda", "Centrafrique", "Mozambique",
        "Madagascar", "Maurice", "RD Congo", "Soudan du Sud",
    ],
    "Asie et Océanie": [
        "Kazakhstan", "Corée du Sud", "Sri Lanka", "Philippines", "Myanmar",
        "Bangladesh", "Thaïlande", "Japon", "Mongolie", "Indonésie",
        "Papouasie-Nouvelle-Guinée", "Timor oriental", "Singapour",
    ],
    "Amériques": [
        "Brésil", "États-Unis", "Cuba", "Mexique", "Colombie", "Pérou", "Chili",
        "Bolivie", "Paraguay", "Équateur", "Panama", "Canada",
    ],
}

# Le dictionnaire « à l'envers » : pays -> région
PAYS_VERS_REGION = {pays: region for region, liste in REGIONS.items() for pays in liste}


def region_du_discours(d):
    """Vatican / Rome, Italie, une des grandes régions, ou None (avion, lieu inconnu)."""
    if d["pays"] in ("Vatican / Rome", "Italie"):
        return d["pays"]
    return PAYS_VERS_REGION.get(d["pays"])


# Le public n'est écrit nulle part : on le devine à partir des mots du titre
# (« Aux évêques de... », « Rencontre avec les jeunes... »). Les catégories sont
# testées dans l'ordre et la première qui correspond l'emporte.
PUBLICS = [
    ("journalistes", ["journaliste", "presse", " vol "]),
    ("autorités et diplomates", ["autorités", "diplomatique", "ambassadeur", "président",
                                 "parlement", "gouvernement", "société civile", "nations unies",
                                 "conseil de l'europe", "maire"]),
    ("œcuménique et interreligieux", ["œcuméni", "orthodoxe", "patriarc", "juif", "juive",
                                      "rabbin", "musulman", "islam", "interreligi",
                                      "luthérien", "anglican", "religions"]),
    ("jeunes", ["jeunes", "étudiants", "élèves", "enfants", "université"]),
    ("clergé et religieux", ["évêque", "prêtre", "séminariste", "clergé", "religieux",
                             "religieuses", "chapitre général", "synod", "curie", "cardinaux",
                             "consacré", "nonce", "ad limina", "épiscopal", "sœurs",
                             "pères", "frères", "missionnaires", "diacres", "congrégation"]),
]
PUBLIC_PAR_DEFAUT = "fidèles et autres"   # tout ce qui ne rentre dans aucune case


def public_du_discours(d):
    """Devine le public d'un discours à partir de son titre."""
    # Les espaces autour du titre permettent de repérer le mot isolé " vol "
    titre = " " + d["titre"].lower() + " "
    for public, mots_cles in PUBLICS:
        if any(mot in titre for mot in mots_cles):
            return public
    return PUBLIC_PAR_DEFAUT


def tableau_par_discours(discours):
    """Le tableau de données de la régression : une ligne par discours.

    Colonnes : region, public, annee, nb_mots, puis une colonne par thème
    (nombre d'emplois des mots du thème dans le discours).
    Les discours dans l'avion ou de lieu inconnu sont écartés : ils n'ont pas de région.
    """
    lignes = []
    for d in discours:
        region = region_du_discours(d)
        if region is None or d["nb_mots"] == 0:
            continue
        ligne = {"region": region, "public": public_du_discours(d),
                 "annee": d["date"][:4], "nb_mots": d["nb_mots"]}
        for theme, mots in THEMES.items():
            ligne[theme] = occurrences_du_theme(d, mots)
        lignes.append(ligne)
    return pd.DataFrame(lignes)


# ======================================================================
# 3. La régression binomiale négative
# ======================================================================

# Formule au format statsmodels. C(...) transforme la variable en indicatrices ;
# Treatment("...") choisit la modalité de référence (celle qui n'a pas de coefficient).
# L'année n'a pas de référence imposée : c'est la première, 2013.
FORMULE = ('y ~ C(region, Treatment("Vatican / Rome"))'
           ' + C(public, Treatment("' + PUBLIC_PAR_DEFAUT + '"))'
           ' + C(annee)')


def nom_lisible(variable):
    """Traduit les noms de statsmodels : 'C(region, ...)[T.Afrique]' -> 'région : Afrique'."""
    if "[T." not in variable:
        return variable
    valeur = variable.split("[T.")[1].rstrip("]")
    if variable.startswith("C(region"):
        return "région : " + valeur
    if variable.startswith("C(public"):
        return "public : " + valeur
    if variable.startswith("C(annee"):
        return "année : " + valeur
    return variable


def etoiles(p):
    """Les étoiles habituelles des tableaux de régression."""
    if p < 0.001:
        return "***"
    if p < 0.01:
        return "**"
    if p < 0.05:
        return "*"
    return ""


def regression_theme(theme, tableau):
    """Régression binomiale négative pour un thème.

    Renvoie (resultat, coefficients) :
    - resultat : l'objet statsmodels complet (print(resultat.summary()) pour tout voir) ;
    - coefficients : un tableau lisible des effets de la région et du public, avec
      rapport de taux, intervalle à 95 %, p-value et étoiles. Les années servent de
      contrôle mais ne sont pas affichées.
    """
    donnees = tableau.assign(y=tableau[theme])
    # offset = log(nombre de mots) : on modélise le nombre de mots du thème PAR MOT prononcé
    modele = smf.negativebinomial(FORMULE, data=donnees, offset=np.log(donnees["nb_mots"]))
    resultat = modele.fit(disp=0, maxiter=300)   # disp=0 : pas de messages pendant le calcul

    # Le modèle est en log : exp(coefficient) donne un effet multiplicatif, le « rapport de taux »
    intervalle = resultat.conf_int()
    coefficients = pd.DataFrame({
        "variable": [nom_lisible(v) for v in resultat.params.index],
        "rapport_de_taux": np.exp(resultat.params).round(2).values,
        "ic_bas": np.exp(intervalle[0]).round(2).values,
        "ic_haut": np.exp(intervalle[1]).round(2).values,
        "p_value": resultat.pvalues.round(4).values,
    })
    coefficients["signif"] = coefficients["p_value"].apply(etoiles)

    # On ne montre que la région et le public (pas la constante, les années ni alpha)
    a_garder = coefficients["variable"].str.startswith(("région", "public"))
    return resultat, coefficients[a_garder].reset_index(drop=True)


def regressions_tous_les_themes(tableau):
    """Les coefficients des 12 régressions, empilés dans un seul tableau."""
    tableaux = []
    for theme in THEMES:
        _, coefficients = regression_theme(theme, tableau)
        coefficients.insert(0, "theme", theme)
        tableaux.append(coefficients)
    return pd.concat(tableaux, ignore_index=True)


def resume_regressions(tableau):
    """Tableau croisé : une ligne par variable, une colonne par thème.

    Chaque case contient le rapport de taux suivi de ses étoiles, par exemple « 2.31** ».
    Il se lit colonne par colonne : un thème, et ce qui le fait monter ou baisser.
    """
    tous = regressions_tous_les_themes(tableau)
    tous["case"] = tous["rapport_de_taux"].map("{:.2f}".format) + tous["signif"]
    resume = tous.pivot(index="variable", columns="theme", values="case")
    # pivot trie par ordre alphabétique : on remet les régions puis les publics,
    # et les thèmes dans l'ordre de themes.py
    ordre_des_lignes = tous["variable"].drop_duplicates()
    return resume.loc[ordre_des_lignes, list(THEMES)]


# ======================================================================
# 4. La démarche déroulée sur un exemple, avec les vrais chiffres
# ======================================================================

def expliquer_demarche(discours, theme="paix et guerre", pays="Irak", n_tirages=1000):
    """Affiche pas à pas tout le raisonnement pour un thème et un pays.

    Pratique pour l'oral ou le rapport : chaque étape est expliquée avec les
    vrais chiffres du corpus.
    """
    mots = THEMES[theme]
    discours_du_pays = ranger_par_lieu(discours)[pays]
    n = len(discours_du_pays)

    def titre(texte):
        print("\n" + texte)
        print("-" * len(texte))

    print(f"LA DÉMARCHE SUR UN EXEMPLE : « {theme} » dans le pays « {pays} »")

    # ----- Étape 1 : l'indice -----
    titre("Étape 1. L'indice")
    occurrences = sum(occurrences_du_theme(d, mots) for d in discours_du_pays)
    nb_mots = sum(d["nb_mots"] for d in discours_du_pays)
    frequence_pays = occurrences / nb_mots
    frequence_globale = frequence_dans_le_corpus(mots, discours)
    indice = frequence_pays / frequence_globale
    mots_lisible = f"{nb_mots:,}".replace(",", " ")   # 7773 -> "7 773"
    print(f"{pays} : {n} discours, {mots_lisible} mots, dont {occurrences} mots du thème")
    print(f"  -> {10000 * frequence_pays:.1f} mots du thème pour 10 000 mots prononcés")
    print(f"Dans tout le corpus : {10000 * frequence_globale:.1f} pour 10 000 mots")
    print(f"Indice = {10000 * frequence_pays:.1f} / {10000 * frequence_globale:.1f} = {indice:.2f}")
    print(f"Lecture : il emploie les mots du thème {indice:.1f} fois "
          f"{'plus' if indice >= 1 else 'moins'} que d'habitude... mais est-ce solide ?")

    # ----- Étape 2 : le bootstrap -----
    titre("Étape 2. Le hasard : le bootstrap")
    print(f"On « rejoue » le voyage : on tire {n} discours au hasard parmi les {n}, avec remise,")
    print("et on recalcule l'indice. Trois tirages pour l'exemple :")
    hasard = np.random.default_rng(0)
    occ = np.array([occurrences_du_theme(d, mots) for d in discours_du_pays])
    mots_par_discours = np.array([d["nb_mots"] for d in discours_du_pays])
    for numero in range(1, 4):
        tirage = hasard.integers(0, n, size=n)
        indice_tire = occ[tirage].sum() / mots_par_discours[tirage].sum() / frequence_globale
        dates = ", ".join(discours_du_pays[i]["date"] for i in sorted(tirage))
        print(f"  tirage {numero} : discours du {dates}")
        print(f"             -> indice {indice_tire:.2f}")

    tirages = hasard.integers(0, n, size=(n_tirages, n))
    simules = occ[tirages].sum(axis=1) / mots_par_discours[tirages].sum(axis=1) / frequence_globale
    ic_bas, ic_haut = np.quantile(simules, [0.025, 0.975])
    print(f"On recommence {n_tirages} fois. Les indices simulés vont de {simules.min():.2f} "
          f"à {simules.max():.2f}.")
    print(f"On garde les 95 % du milieu : intervalle de confiance = [{ic_bas:.2f} ; {ic_haut:.2f}]")
    if ic_bas > 1:
        print("Conclusion : l'intervalle est entièrement au-dessus de 1. Quels que soient les")
        print("discours tirés, l'indice reste au-dessus de la moyenne : l'écart est SIGNIFICATIF.")
    elif ic_haut < 1:
        print("Conclusion : l'intervalle est entièrement en dessous de 1 : il en parle")
        print("SIGNIFICATIVEMENT MOINS ici.")
    else:
        print("Conclusion : l'intervalle contient 1. Selon les discours tirés, l'indice passe")
        print("au-dessus ou en dessous de la moyenne : on NE PEUT PAS CONCLURE.")

    # ----- Étape 3 : la régression -----
    titre("Étape 3. Les facteurs de confusion : la régression")
    region = PAYS_VERS_REGION.get(pays, pays)
    print(f"Le pays est rangé dans la région « {region} ». La régression compare chaque")
    print("discours à un discours prononcé au Vatican, devant des fidèles, la même année.")
    tableau = tableau_par_discours(discours)
    resultat, coefficients = regression_theme(theme, tableau)
    ligne = coefficients[coefficients["variable"] == "région : " + region]
    if ligne.empty:
        print("(pas de coefficient pour cette région)")
    else:
        c = ligne.iloc[0]
        print(f"Rapport de taux de la région : ×{c['rapport_de_taux']:.2f} "
              f"[{c['ic_bas']:.2f} ; {c['ic_haut']:.2f}], p-value = {c['p_value']:.4f} {c['signif']}")
        if c["p_value"] < 0.05:
            sens = "plus" if c["rapport_de_taux"] > 1 else "moins"
            print(f"Lecture : à public et année égaux, il emploie {c['rapport_de_taux']:.2f} fois les mots")
            print(f"du thème dans cette région par rapport au Vatican : il en parle {sens}, et ce")
            print("n'est pas seulement dû au public auquel il s'adresse.")
        else:
            print("Lecture : une fois le public et l'année pris en compte, la région n'a pas")
            print("d'effet significatif. L'écart de l'indice venait sans doute du public.")
    print(f"(alpha, le paramètre de surdispersion, vaut {resultat.params['alpha']:.2f} : "
          "s'il valait 0, une loi de Poisson aurait suffi)")

    # ----- Étape 4 : bilan -----
    titre("Étape 4. Ce qu'on en retient")
    print(f"- Indice brut : {indice:.2f}")
    significatif = ic_bas > 1 or ic_haut < 1
    print(f"- Bootstrap : [{ic_bas:.2f} ; {ic_haut:.2f}] -> l'écart du pays "
          + ("est significatif" if significatif else "n'est pas significatif"))
    print("- Régression : effet de la région une fois le public et l'année contrôlés")
    print("Ce sont des corrélations, pas des causes : le programme d'un voyage dépend du pays.")


# ======================================================================
# Lancement direct : python analyse_discours/robustesse.py
# ======================================================================

if __name__ == "__main__":
    from chercher_mot import charger_discours
    from statistiques import preparer_discours

    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", 20)

    print("Chargement des discours...")
    discours = preparer_discours(charger_discours())
    DOSSIER_RESULTATS.mkdir(exist_ok=True)

    # 0. La démarche expliquée sur un exemple
    expliquer_demarche(discours, theme="paix et guerre", pays="Irak")

    # 1. Bootstrap pour tous les thèmes et tous les pays
    print("\n\n=== 1. Intervalles de confiance pour tous les thèmes ===")
    bootstrap = bootstrap_tous_les_themes(discours)
    chemin = DOSSIER_RESULTATS / "bootstrap_themes_pays.csv"
    bootstrap.to_csv(chemin, index=False, encoding="utf-8-sig")
    avec_ic = bootstrap[bootstrap["ic_bas"].notna()]
    print(f"Sur {len(avec_ic)} couples (thème, pays) avec au moins 3 discours :")
    print(avec_ic["conclusion"].value_counts().to_string())
    print("Tableau complet :", chemin)

    # 2. Régressions pour tous les thèmes
    print("\n=== 2. Régressions binomiales négatives (une par thème) ===")
    tableau = tableau_par_discours(discours)
    print(f"{len(tableau)} discours utilisés.")
    resume = resume_regressions(tableau)
    chemin = DOSSIER_RESULTATS / "regressions_themes.csv"
    resume.to_csv(chemin, encoding="utf-8-sig")
    print("Rapports de taux (* p<0,05  ** p<0,01  *** p<0,001) :")
    print(resume.to_string())
    print("Tableau enregistré :", chemin)
