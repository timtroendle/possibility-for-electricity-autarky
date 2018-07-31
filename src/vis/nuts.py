"""This module visualises distribution of NUTS units."""
import click
import matplotlib.pyplot as plt
import pandas as pd
import geopandas as gpd
import seaborn as sns

from src.conversion import area_in_squaremeters


@click.command()
@click.argument('path_to_nuts')
@click.argument('path_to_figure')
def visualise_nuts_distributions(path_to_nuts, path_to_figure):
    """Visualise distributions of NUTS units."""
    sns.set_context('paper')
    sns.set_style("whitegrid")

    nuts = gpd.read_file(path_to_nuts)
    nuts = nuts.rename(columns={"STAT_LEVL_": "NUTS LEVEL"})
    nuts["area"] = area_in_squaremeters(nuts)
    nuts["population sum"] = nuts["population_sum"]
    nuts["population density"] = nuts["population_sum"] / nuts["area"]

    fig = plt.figure(figsize=(8, 8))
    fig.suptitle("Regions in different NUTS levels")

    ax1 = fig.add_subplot(311)
    boxplot(
        nuts=nuts,
        column="area",
        ax=ax1
    )
    ax2 = fig.add_subplot(312)
    boxplot(
        nuts=nuts,
        column="population sum",
        ax=ax2
    )
    ax3 = fig.add_subplot(313)
    boxplot(
        nuts=nuts,
        column="population density",
        ax=ax3
    )
    _ = plt.xlabel("NUTS level")

    harmonise_ylimits([ax1, ax2, ax3])

    fig.savefig(path_to_figure, dpi=300)


def boxplot(nuts, column, ax):
    sns.boxplot(
        data=pd.DataFrame({
            "NUTS LEVEL": nuts["NUTS LEVEL"],
            column: nuts.groupby("NUTS LEVEL")[column].transform(normalise_series),
        }),
        x="NUTS LEVEL",
        y=column,
        ax=ax
    )
    ax.set_yscale('log')
    _ = plt.ylabel("relative {}".format(column))
    _ = plt.xlabel("")


def harmonise_ylimits(axes):
    ymin = min([ax.get_ylim()[0] for ax in axes])
    ymax = max([ax.get_ylim()[1] for ax in axes])
    for ax in axes:
        ax.set_ylim(ymin, ymax)


def normalise_series(series):
    return series / series.max()


if __name__ == "__main__":
    visualise_nuts_distributions()
