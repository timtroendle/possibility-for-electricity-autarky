"""Visualises the fraction of land needed to fulfill demand in each region in Germany."""
import click
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import seaborn as sns

from src.conversion import coordinate_string_to_decimal

LAND_THRESHOLD = 0.3 # fraction of land that can be used for energy farming
KASSEL_COORDINATES = "51°19′N 9°30′E"
GREEN = "#679436"
RED = "#A01914"


@click.command()
@click.argument("path_to_regions")
@click.argument("path_to_necessary_land")
@click.argument("path_to_countries")
@click.argument("path_to_map")
def visualise_necessary_land(path_to_regions, path_to_necessary_land, path_to_countries, path_to_map):
    """Visualise fraction of necessary land needed to fulfill demand in each region in Germany."""
    sns.set_context('paper')
    regions = gpd.read_file(path_to_regions).merge(pd.read_csv(path_to_necessary_land), on="id")
    countries = gpd.read_file(path_to_countries)
    _map(regions, countries, path_to_map)


def _map(regions, countries, path_to_plot):
    winners = regions[regions["fraction_land_necessary"] <= LAND_THRESHOLD]
    loosers = regions[regions["fraction_land_necessary"] > LAND_THRESHOLD]
    de_winners = winners[winners.country_code == "DEU"]
    de_loosers = loosers[loosers.country_code == "DEU"]
    invalids = regions[~regions.isin(pd.concat([winners, loosers]))].dropna()
    kassel_x, kassel_y = coordinate_string_to_decimal(KASSEL_COORDINATES)

    fig = plt.figure(figsize=(9, 10))
    ax = fig.add_subplot(111)
    _third_countries(countries).plot(
        color='grey', edgecolor='black', linewidth=0.4, ax=ax, alpha=0.2
    )
    countries.plot(color='white', edgecolor='black', linewidth=0.8, ax=ax)
    winners.plot(color=GREEN, linewidth=0.1, ax=ax, alpha=0.5)
    loosers.plot(color=RED, linewidth=0.1, ax=ax, alpha=0.5)
    de_winners.plot(color=GREEN, linewidth=0.1, ax=ax)
    de_loosers.plot(color=RED, linewidth=0.1, ax=ax)
    if not invalids.empty:
        invalids.plot(color="grey", linewidth=0.1, ax=ax)
    ax.plot(
        [kassel_x], [kassel_y],
        color="black", marker="o", markersize=6
    )
    ax.text(x=kassel_x - 0.3, y=kassel_y - 0.25, s="Kassel")
    ax.set_xlim(5, 16)
    ax.set_ylim(46.5, 56)
    ax.set_xticks([])
    ax.set_yticks([])
    fig.savefig(path_to_plot, dpi=300)


def _third_countries(countries):
    world = gpd.read_file(gpd.datasets.get_path('naturalearth_lowres'))
    return world[~world.iso_a3.isin(countries.country_code.unique())]


if __name__ == "__main__":
    visualise_necessary_land()
