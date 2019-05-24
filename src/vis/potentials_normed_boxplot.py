"""Visualises the range of potentials relative to demand in each municipality."""
from itertools import chain, repeat

import click
import pandas as pd
import geopandas as gpd
import matplotlib
import matplotlib.pyplot as plt
import seaborn as sns
import pycountry


from src.vis import RED, GREEN, BLUE

SORT_QUANTILE = 0.5


@click.command()
@click.argument("path_to_results")
@click.argument("path_to_plot")
def visualise_normed_potentials(path_to_results, path_to_plot):
    """Visualises the range of potentials relative to demand in each municipality."""
    sns.set_context('paper')
    units = pd.DataFrame(gpd.read_file(path_to_results))
    units = units[["country_code", "population_sum", "normed_potential"]]
    units["country"] = units["country_code"].map(lambda country_code: pycountry.countries.lookup(country_code).name)
    units["country"].replace("Macedonia, Republic of", value="Macedonia", inplace=True) # too long
    units["country"].replace("Bosnia and Herzegovina", value="Bosnia", inplace=True) # too long
    people = pd.DataFrame(
        data={
            "country": list(chain(*[
                (repeat(unit[1].country, round(unit[1].population_sum / 100)))
                for unit in units.iterrows()
            ])),
            "normed_potential": list(chain(*[
                (repeat(unit[1].normed_potential, round(unit[1].population_sum / 100)))
                for unit in units.iterrows()
            ]))
        }
    )

    people_eu = people.copy()
    people_eu["country"] = "Europe"
    people = pd.concat([people, people_eu])

    fig = plt.figure(figsize=(7, 8.75), constrained_layout=True)
    ax = fig.add_subplot(111)
    sns.boxplot(
        data=people,
        x="normed_potential",
        y="country",
        order=people.groupby("country").normed_potential.quantile(SORT_QUANTILE).sort_values().index,
        ax=ax,
        color=GREEN,
        whis=[2.5, 97.5],
        saturation=0.85,
        linewidth=1.3,
        width=0.7,
        boxprops=dict(linewidth=1.3, edgecolor=GREEN),
        whiskerprops=dict(linewidth=1, color=GREEN),
        flierprops=dict(markerfacecolor="k", markeredgecolor="k", markersize=0, marker="o"),
        capprops=dict(color=GREEN)

    )
    ax.axvline(1, color=RED, linewidth=1.5)
    ax.set_xlabel("potential relative to demand")
    ax.set_ylabel("country")
    ax.set_xscale('log')
    ax.set_xlim(0.08, 100)
    ax.set_xticklabels(["{:.0f}%".format(tick * 100) for tick in ax.get_xticks()])
    eu_position = list(
        people.groupby("country").normed_potential.quantile(SORT_QUANTILE).sort_values().index
    ).index("Europe")
    eu_patch = [child for child in ax.get_children() if isinstance(child, matplotlib.patches.PathPatch)][eu_position]
    eu_patch.set_facecolor(BLUE)
    eu_patch.set_edgecolor(BLUE)
    eu_patch.set_alpha(0.8)
    eu_patch.set_zorder(100000)
    if path_to_plot[-3:] == "png":
        fig.savefig(path_to_plot, dpi=300, transparent=True)
    else:
        fig.savefig(path_to_plot, dpi=600, transparent=False, pil_kwargs={"compression": "tiff_lzw"})


if __name__ == "__main__":
    visualise_normed_potentials()
