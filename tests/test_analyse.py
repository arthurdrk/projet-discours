"""Tests des fonctions de robustesse sur un petit corpus inventé, sans accès au réseau."""
import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "outils"))
import robustness as rb  # noqa: E402

LEXIQUE = {"Paix": r"\bpeace\b"}


def petit_corpus():
    textes = ["peace peace and more", "peace is near", "a speech about nothing",
              "nothing here", "still nothing", "peace"]
    return pd.DataFrame({"text": textes,
                         "n_mots": [len(t.split()) for t in textes],
                         "continent": ["A", "A", "A", "B", "B", "B"]})


class TestRobustesse(unittest.TestCase):
    def test_mentions(self):
        self.assertEqual(rb.mentions(petit_corpus(), LEXIQUE)["Paix"].tolist(), [2, 1, 0, 0, 0, 1])

    def test_indice_du_bootstrap(self):
        df = petit_corpus()
        resultat = rb.bootstrap(df, "continent", LEXIQUE, draws=200, minimum=3).set_index("continent")
        taux_global = 4 / df["n_mots"].sum()
        self.assertAlmostEqual(resultat.loc["A", "index"], (3 / 11) / taux_global)
        self.assertAlmostEqual(resultat.loc["B", "index"], (1 / 5) / taux_global)
        # L'intervalle encadre l'indice observé
        for _, ligne in resultat.iterrows():
            self.assertLessEqual(ligne["low"], ligne["index"])
            self.assertGreaterEqual(ligne["high"], ligne["index"])

    def test_groupes_trop_petits_ecartes(self):
        resultat = rb.bootstrap(petit_corpus(), "continent", LEXIQUE, draws=50, minimum=4)
        self.assertTrue(resultat.empty)


if __name__ == "__main__":
    unittest.main()
