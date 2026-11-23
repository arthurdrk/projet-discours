"""Couleurs et mise en forme communes aux graphiques du rapport (Plotly)."""
import plotly.graph_objects as go
import plotly.io as pio

from analyse_corpus import ORDRE_CONTINENTS

FOND = "#fcfcfb"
ENCRE = "#0b0b0b"
ENCRE_2 = "#52514e"
GRIS = "#898781"
GRILLE = "#e1e0d9"
AXE = "#c3c2b7"
POLICE = "system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif"

# Une couleur par catégorie, toujours dans le même ordre (testé pour les daltonismes courants).
COULEURS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
COULEUR_CONTINENT = dict(zip(ORDRE_CONTINENTS, COULEURS))

# Dégradé d'une seule teinte, du plus clair au plus foncé, pour les intensités.
BLEUS = ["#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec", "#5598e7", "#3987e5",
         "#2a78d6", "#256abf", "#1c5cab", "#184f95", "#104281", "#0d366b"]
ECHELLE_BLEUE = [[i / (len(BLEUS) - 1), couleur] for i, couleur in enumerate(BLEUS)]


def style():
    """Modèle Plotly du rapport : fond clair, grille discrète, titres alignés à gauche."""
    pio.templates["rapport"] = go.layout.Template(layout=dict(
        font=dict(family=POLICE, size=13, color=ENCRE_2),
        paper_bgcolor=FOND, plot_bgcolor=FOND, colorway=COULEURS,
        title=dict(x=0.01, xref="container", xanchor="left", y=1, yref="container", yanchor="top",
                   pad=dict(t=16), font=dict(size=18, color=ENCRE)),
        xaxis=dict(gridcolor=GRILLE, linecolor=AXE, showline=True, zeroline=False, showgrid=False),
        yaxis=dict(gridcolor=GRILLE, linecolor=AXE, showline=False, zeroline=False, showgrid=False),
        legend=dict(orientation="h", x=0, xanchor="left", y=1.0, yanchor="bottom"),
        hoverlabel=dict(bgcolor="white", bordercolor=GRILLE, font=dict(family=POLICE, size=12, color=ENCRE)),
        annotationdefaults=dict(font=dict(size=14, color=ENCRE)),
        margin=dict(l=20, r=30, b=50),
        bargap=0.35,
    ))
    pio.templates.default = "plotly_white+rapport"
    pio.renderers.default = "plotly_mimetype+notebook_connected"


def titre(fig, texte, sous_titre=None, hauteur=450, marge_haute=0):
    """Titre, petite ligne grise en dessous et hauteur du graphique."""
    legende = sum(1 for trace in fig.data if trace.showlegend is not False and trace.name) > 1
    haut = 60 + (25 if sous_titre else 0) + (30 if legende else 0) + marge_haute
    fig.update_layout(height=hauteur, legend_title_text="", margin_t=haut,
                      title=dict(text=texte, subtitle=dict(text=sous_titre or "", font=dict(size=13, color=GRIS))))
    return fig


def carte_chaleur(valeurs, texte, sous_titre=None):
    """Tableau coloré ligne par ligne : case la plus foncée au maximum de la ligne, la plus claire au minimum."""
    relatif = valeurs.sub(valeurs.min(axis=1), axis=0).div(valeurs.max(axis=1) - valeurs.min(axis=1), axis=0)
    fig = go.Figure(go.Heatmap(
        z=relatif, x=list(valeurs.columns), y=list(valeurs.index), customdata=valeurs,
        text=valeurs.round(0).astype(int), texttemplate="%{text}", colorscale=ECHELLE_BLEUE, showscale=False,
        xgap=2, ygap=2, hovertemplate="%{y}, %{x}<br>%{customdata:.1f} mentions pour 10 000 mots<extra></extra>"))
    fig.update_xaxes(side="top", showline=False)
    fig.update_yaxes(autorange="reversed")
    lignes = max(str(colonne).count("<br>") + 1 for colonne in valeurs.columns)
    return titre(fig, texte, sous_titre, hauteur=38 * len(valeurs) + 170 + 18 * lignes, marge_haute=18 * lignes)
