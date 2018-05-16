"""Visualises the fraction of land needed to fulfill demand in each region."""
import click
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import seaborn as sns

from src.conversion import area_in_squaremeters

LAND_THRESHOLD = 0.3 # fraction of land that can be used for energy farming
GREEN = "#679436"
RED = "#A01914"


@click.command()
@click.argument("paths_to_results", nargs=-1)
@click.argument("path_to_countries")
@click.argument("path_to_boxplot")
@click.argument("path_to_map")
@click.argument("path_to_correlation")
def visualise_necessary_land(paths_to_results, path_to_countries, path_to_boxplot, path_to_map, path_to_correlation):
    """Visualise fraction of necessary land needed to fulfill demand in each region.

    Creates:
    * boxplot for each country
    * red/green map
    * plot of correlation of region features to necessary land
    """
    sns.set_context('paper')
    paths_to_results = [paths.split(",") for paths in paths_to_results]
    region_sets = [
        gpd.read_file(paths[0]).merge(
            pd.concat([pd.read_csv(p, index_col=0) for p in paths[1:]], axis=1).reset_index(),
            on="id"
        )
        for paths in paths_to_results
    ]
    for region, paths_to_region in zip(region_sets, paths_to_results):
        region["layer_id"] = _infer_layer_id(paths_to_region[0])
    countries = gpd.read_file(path_to_countries)
    _boxplot([region_sets[0], region_sets[-1]], path_to_boxplot)
    _correlation(region_sets, path_to_correlation)
    _map(region_sets[-1], countries, path_to_map)


def _boxplot(region_sets, path_to_plot):
    data = pd.concat([pd.DataFrame(gdf) for gdf in region_sets])
    data_eu = data.copy()
    data_eu["country_code"] = "EUR"
    data = pd.concat([data, data_eu])

    fig = plt.figure(figsize=(8, 10))
    ax = fig.add_subplot(111)
    sns.boxplot(
        data=data,
        x="fraction_land_necessary",
        y="country_code",
        hue="layer_id",
        order=data.groupby("country_code").fraction_land_necessary.quantile(0.75).sort_values().index,
        ax=ax
    )
    ax.set_xlabel("fraction land necessary")
    ax.set_ylabel("country code")
    ax.set_xscale('log')
    ax.axvline(1, color="r", linewidth=0.75)
    fig.savefig(path_to_plot, dpi=300)


def _map(regions, countries, path_to_plot):
    winners = regions[regions["fraction_land_necessary"] <= LAND_THRESHOLD]
    loosers = regions[regions["fraction_land_necessary"] > LAND_THRESHOLD]
    invalids = regions[~regions.isin(pd.concat([winners, loosers]))].dropna()

    fig = plt.figure(figsize=(16, 16))
    ax = fig.add_subplot(111)
    _third_countries(countries).plot(
        color='grey', edgecolor='black', linewidth=0.4, ax=ax, alpha=0.2
    )
    countries.plot(color='white', edgecolor='black', linewidth=0.4, ax=ax)
    winners.plot(color=GREEN, linewidth=0.1, ax=ax)
    loosers.plot(color=RED, linewidth=0.1, ax=ax)
    if not invalids.empty:
        invalids.plot(color="grey", linewidth=0.1, ax=ax)
    ax.set_xlim(-15, 30)
    ax.set_ylim(30, 70)
    ax.set_xticks([])
    ax.set_yticks([])
    fig.savefig(path_to_plot, dpi=300)


def _correlation(region_sets, path_to_plot):
    fig = plt.figure(figsize=(8, 5))
    ax1 = fig.add_subplot(121)
    for region_set in reversed(region_sets):
        layer_id = region_set["layer_id"][0]
        region_set["area_km2"] = area_in_squaremeters(region_set) / 1e6
        sns.regplot(
            data=region_set,
            x="area_km2",
            y="fraction_land_necessary",
            label=layer_id,
            fit_reg=False,
            ax=ax1
        )
    ax1.axhline(1, color="r", linewidth=0.75)
    berlin = region_sets[1].set_index("name").loc["Berlin"]
    ax1.plot(
        [berlin.area_km2], [berlin.fraction_land_necessary],
        color="red", marker="o", markersize=6
    )
    ax1.text(x=berlin.area_km2 + 500, y=berlin.fraction_land_necessary - 0.02, s="Berlin")
    ax1.set_xticks([0, 40000, 80000, 120000])
    ax1.set_xlabel("region size [km^2]")
    ax1.set_ylabel("fraction of eligible land necessary")
    ax1.set_xlim(0.1,)
    ax1.set_ylim(0, 2)
    ax1.set_xscale("log")
    ax1.legend()

    ax2 = fig.add_subplot(122, sharey=ax1)
    for region_set in reversed(region_sets):
        layer_id = region_set["layer_id"][0]
        region_set["population_density"] = region_set["population_sum"] / region_set["area_km2"]
        sns.regplot(
            data=region_set,
            x="population_density",
            y="fraction_land_necessary",
            label=layer_id,
            fit_reg=False,
            ax=ax2
        )
    ax2.axhline(1, color="r", linewidth=0.75)
    berlin = region_sets[1].set_index("name").loc["Berlin"]
    ax2.plot(
        [berlin.population_density], [berlin.fraction_land_necessary],
        color="red", marker="o", markersize=6
    )
    ax2.text(x=berlin.population_density + 2000, y=berlin.fraction_land_necessary - 0.02, s="Berlin")
    ax2.set_ylabel("")
    ax2.set_xlabel("population density [p/km^2]")
    ax2.set_xlim(0.1,)
    ax2.set_ylim(0, 2)
    ax2.set_xscale("log")
    ax2.legend()

    fig.savefig(path_to_plot, dpi=300)


def _third_countries(countries):
    world = gpd.read_file(gpd.datasets.get_path('naturalearth_lowres'))
    return world[~world.iso_a3.isin(countries.country_code.unique())]


def _infer_layer_id(path_to_regions):
    # based on the idea, that paths are something like 'build/adm2/blabla.geojson'
    # FIXME should be a more robust approach
    return path_to_regions.split("/")[1]


if __name__ == "__main__":
    visualise_necessary_land()
