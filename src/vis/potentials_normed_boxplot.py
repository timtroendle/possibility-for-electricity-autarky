"""Visualises the range of potentials relative to demand in each municipality."""
import click
import pandas as pd
import geopandas as gpd
import matplotlib
import matplotlib.pyplot as plt
import seaborn as sns


from src.vis.potentials_normed import RED, GREEN, BLUE


@click.command()
@click.argument("path_to_results")
@click.argument("path_to_plot")
def visualise_normed_potentials(path_to_results, path_to_plot):
    """Visualises the range of potentials relative to demand in each municipality."""
    sns.set_context('paper')
    data = pd.DataFrame(gpd.read_file(path_to_results))
    data_eu = data.copy()
    data_eu["country_code"] = "EUR"
    data = pd.concat([data, data_eu])

    fig = plt.figure(figsize=(8, 10), constrained_layout=True)
    ax = fig.add_subplot(111)
    sns.boxplot(
        data=data,
        x="normed_potential",
        y="country_code",
        order=data.groupby("country_code").normed_potential.quantile(0.5).sort_values().index,
        ax=ax,
        color=GREEN,
        whis=1.5,
        saturation=0.85,
        linewidth=1.3,
        width=0.7,
        boxprops=dict(linewidth=1.3, edgecolor=GREEN),
        whiskerprops=dict(linewidth=1, color=GREEN),
        flierprops=dict(markerfacecolor="k", markeredgecolor="k", markersize=2, marker="o"),
        capprops=dict(color=GREEN)

    )
    ax.set_xlabel("potential relative to demand [-]")
    ax.set_ylabel("country code")
    ax.set_xscale('log')
    ax.set_xlim(0.008, 1000)
    ax.axvline(1, color=RED, linewidth=1.5)
    eu_position = list(data.groupby("country_code").normed_potential.quantile(0.5).sort_values().index).index("EUR")
    eu_patch = [child for child in ax.get_children() if isinstance(child, matplotlib.patches.PathPatch)][eu_position]
    eu_patch.set_facecolor(BLUE)
    eu_patch.set_edgecolor(BLUE)
    eu_patch.set_alpha(0.8)
    eu_patch.set_zorder(100000)
    fig.savefig(path_to_plot, dpi=300)


if __name__ == "__main__":
    visualise_normed_potentials()
