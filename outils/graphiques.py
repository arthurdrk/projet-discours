"""Couleurs et réglages communs aux graphiques du rapport."""
import matplotlib as mpl
import numpy as np
from matplotlib import font_manager
from matplotlib.colors import LinearSegmentedColormap

from analyse_corpus import ORDRE_CONTINENTS

FOND = "#fcfcfb"
ENCRE = "#0b0b0b"
ENCRE_2 = "#52514e"
GRIS = "#898781"
GRILLE = "#e1e0d9"
AXE = "#c3c2b7"

# Une couleur par catégorie, toujours dans le même ordre (testé pour les daltonismes courants).
COULEURS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
COULEUR_CONTINENT = dict(zip(ORDRE_CONTINENTS, COULEURS))

# Dégradé d'une seule teinte, du plus clair au plus foncé, pour les intensités.
BLEUS = ["#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec", "#5598e7", "#3987e5",
         "#2a78d6", "#256abf", "#1c5cab", "#184f95", "#104281", "#0d366b"]
DEGRADE = LinearSegmentedColormap.from_list("bleus", BLEUS)


def style():
    """Style sobre : fond clair, grille discrète, titres alignés à gauche."""
    installees = {f.name for f in font_manager.fontManager.ttflist}
    polices = [p for p in ("Segoe UI", "DejaVu Sans") if p in installees] + ["sans-serif"]
    mpl.rcParams.update({
        "figure.facecolor": FOND, "axes.facecolor": FOND, "savefig.facecolor": FOND,
        "figure.dpi": 110, "font.family": polices, "font.size": 10.5,
        "axes.edgecolor": AXE, "axes.labelcolor": ENCRE_2, "axes.titlecolor": ENCRE,
        "axes.titlesize": 13, "axes.titleweight": "semibold", "axes.titlelocation": "left", "axes.titlepad": 12,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "grid.color": GRILLE, "grid.linewidth": .8, "axes.axisbelow": True,
        "xtick.color": AXE, "ytick.color": AXE, "xtick.labelcolor": ENCRE_2, "ytick.labelcolor": ENCRE_2,
        "legend.frameon": False, "legend.labelcolor": ENCRE_2,
        "lines.linewidth": 2, "lines.solid_capstyle": "round",
    })


def titre(ax, texte, sous_titre=None):
    """Titre du graphique, avec une petite ligne grise en dessous pour dire ce qui est mesuré."""
    ax.set_title(texte, pad=26 if sous_titre else 12)
    if sous_titre:
        ax.annotate(sous_titre, xy=(0, 1), xycoords="axes fraction", xytext=(0, 8), textcoords="offset points",
                    fontsize=9.5, color=GRIS, va="bottom")


def carte_chaleur(ax, valeurs, couleurs=None, fmt="{:.0f}"):
    """Tableau coloré : chaque case porte sa valeur, en blanc sur les cases foncées."""
    couleurs = valeurs if couleurs is None else couleurs
    ax.imshow(couleurs.to_numpy(dtype=float), cmap=DEGRADE, aspect="auto", vmin=0)
    seuil = np.nanmax(couleurs.to_numpy(dtype=float)) * .6
    for i in range(valeurs.shape[0]):
        for j in range(valeurs.shape[1]):
            ax.text(j, i, fmt.format(valeurs.iat[i, j]), ha="center", va="center", fontsize=9,
                    color="white" if couleurs.iat[i, j] > seuil else ENCRE)
    ax.set_xticks(range(valeurs.shape[1]), valeurs.columns)
    ax.set_yticks(range(valeurs.shape[0]), valeurs.index)
    ax.xaxis.tick_top()
    ax.tick_params(length=0)
    ax.grid(False)
    for bord in ax.spines.values():
        bord.set_visible(False)
