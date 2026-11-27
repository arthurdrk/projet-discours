"""Are the differences between groups of speeches robust?

Adapted from Quentin's first analysis to the corpus of 342 speeches.

1. Bootstrap. The index of a theme in a group (a continent, a country) is its rate of mentions
   in the group divided by its rate in the whole corpus. We draw the speeches of the group again
   1,000 times, with replacement, and keep the middle 95 % of the indices: this is the
   confidence interval.
2. Negative binomial regression. For each theme, the number of mentions in a speech is explained
   by the continent, the audience and the year, with the length of the speech as an offset.
"""
import re

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from statsmodels.stats.multitest import multipletests


def mentions(df, lexicon):
    """Number of mentions of each theme in each speech (one column per theme)."""
    return pd.DataFrame({theme: df["text"].str.count(pattern, flags=re.I) for theme, pattern in lexicon.items()})


def bootstrap(df, group, lexicon, draws=1000, minimum=5, seed=0):
    """Index of each theme in each group, with its 95 % confidence interval.

    Groups with fewer than `minimum` speeches are left out.
    """
    rng = np.random.default_rng(seed)   # fixed seed: the same results at each run
    counts = mentions(df, lexicon)
    overall_rate = counts.sum() / df["n_mots"].sum()

    rows = []
    for value, speeches in df.groupby(group).groups.items():
        n = len(speeches)
        if n < minimum:
            continue
        # Each row of `draws_idx` lists n speeches drawn at random, with replacement
        draws_idx = rng.integers(0, n, size=(draws, n))
        words = df.loc[speeches, "n_mots"].to_numpy()
        for theme in lexicon:
            c = counts.loc[speeches, theme].to_numpy()
            indices = c[draws_idx].sum(axis=1) / words[draws_idx].sum(axis=1) / overall_rate[theme]
            low, high = np.quantile(indices, [0.025, 0.975])
            rows.append({group: value, "theme": theme, "speeches": n,
                         "index": c.sum() / words.sum() / overall_rate[theme], "low": low, "high": high})

    result = pd.DataFrame(rows, columns=[group, "theme", "speeches", "index", "low", "high"])
    result["verdict"] = np.select([result["low"] > 1, result["high"] < 1], ["more", "less"], "no clear gap")
    return result


def regressions(df, lexicon, reference_continent, reference_audience):
    """One negative binomial regression per theme. Returns the rate ratios of all variables.

    A rate ratio of 2 for "continent: Africa" means twice as many mentions per word as in the
    reference continent, for the same audience and the same year. The p-values are adjusted
    for the number of tests (Benjamini-Hochberg).
    """
    counts = mentions(df, lexicon)
    formula = (f'y ~ C(continent, Treatment("{reference_continent}"))'
               f' + C(public, Treatment("{reference_audience}")) + year')
    data = df.assign(year=df["annee"] - df["annee"].min())

    rows = []
    for theme in lexicon:
        model = smf.negativebinomial(formula, data=data.assign(y=counts[theme]), offset=np.log(data["n_mots"]))
        fit = model.fit(disp=0, maxiter=500)
        interval = np.exp(fit.conf_int().clip(-50, 50))
        for name in fit.params.index:
            if name in ("Intercept", "alpha"):
                continue
            kind = "Continent" if name.startswith("C(continent") else "Audience" if name.startswith("C(public") else "Year"
            rows.append({"theme": theme, "kind": kind,
                         "variable": name.split("[T.")[1].rstrip("]") if "[T." in name else "One more year",
                         "rate_ratio": np.exp(fit.params[name]),
                         "low": interval.loc[name, 0], "high": interval.loc[name, 1],
                         "p_value": fit.pvalues[name]})

    result = pd.DataFrame(rows)
    # A group that never mentions the theme gives an endless interval: its ratio cannot be estimated
    not_estimable = result["high"] / result["low"] > 1e6
    result.loc[not_estimable, ["rate_ratio", "low", "high"]] = np.nan
    result["p_adjusted"] = multipletests(result["p_value"], method="fdr_bh")[1]
    return result
