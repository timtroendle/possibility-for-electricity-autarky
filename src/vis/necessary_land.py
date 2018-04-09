"""Visualises the fraction of land needed to fulfill demand in each region."""
import click
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.colors
import seaborn as sns

LAND_THRESHOLD = 0.3 # fraction of land that can be used for energy farming


@click.command()
@click.argument("paths_to_regions", nargs=-1)
@click.argument("path_to_countries")
@click.argument("path_to_boxplot")
@click.argument("path_to_map")
def visualise_necessary_land(paths_to_regions, path_to_countries, path_to_boxplot, path_to_map):
    """Visualise fraction of necessary land needed to fulfill demand in each region.

    Creates:
    * boxplot for each country
    * red/green map
    """
    sns.set_context('paper')
    regions = [gpd.read_file(path) for path in paths_to_regions]
    for region, path_to_region in zip(regions, paths_to_regions):
        region["layer_id"] = _infer_layer_id(path_to_region)
    countries = gpd.read_file(path_to_countries, layer="national")
    _boxplot(regions, path_to_boxplot)
    _map(regions[-1], countries, path_to_map)


def _boxplot(regions, path_to_plot):
    fig = plt.figure(figsize=(8, 6))
    ax = fig.add_subplot(111)
    sns.boxplot(
        data=pd.concat([pd.DataFrame(gdf) for gdf in regions]),
        x="country_code",
        y="fraction_land_necessary",
        hue="layer_id",
        ax=ax
    )
    plt.ylabel("fraction land necessary")
    plt.xlabel("country code")
    ax.set_yscale('log')
    fig.autofmt_xdate()
    fig.savefig(path_to_plot, dpi=300)


def _map(regions, countries, path_to_plot):
    regions["sufficient_supply"] = 0
    regions.loc[regions["fraction_land_necessary"] <= LAND_THRESHOLD, "sufficient_supply"] = 1
    regions.loc[regions["fraction_land_necessary"] > LAND_THRESHOLD, "sufficient_supply"] = 2
    levels = [0, 1, 2, 3]
    colors = ['grey', 'green', 'red']
    cmap, norm = matplotlib.colors.from_levels_and_colors(levels, colors)

    fig = plt.figure(figsize=(10, 10))
    ax = fig.add_subplot(111)
    _third_countries(countries).plot(
        color='grey', edgecolor='black', linewidth=0.4, ax=ax, alpha=0.2
    )
    countries.plot(color='white', edgecolor='black', linewidth=0.4, ax=ax)
    regions.plot(column='sufficient_supply', linewidth=0.1, ax=ax, cmap=cmap, vmax=2)
    plt.xlim(-15, 30)
    plt.ylim(30, 70)
    plt.xticks([])
    plt.yticks([])
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
