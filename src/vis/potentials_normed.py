"""Visualises the potentials relative to demand in each region."""
import click
import pandas as pd
import geopandas as gpd
import shapely
from descartes import PolygonPatch
import matplotlib.pyplot as plt
import seaborn as sns

from src.conversion import area_in_squaremeters
from src.eligible_land import FARM, FOREST, GlobCover, ProtectedArea

GREEN = "#679436"
RED = "#A01914"
EPSG_3035_PROJ4 = "+proj=laea +lat_0=52 +lon_0=10 +x_0=4321000 +y_0=3210000 +ellps=GRS80 +units=m +no_defs "
MAP_MIN_X = 2400000
MAP_MIN_Y = 1300000
MAP_MAX_X = 6600000
MAP_MAX_Y = 5400000
SERBIA_PATCH_MIN_X = 5040000
SERBIA_PATCH_MIN_Y = 2200000
SERBIA_PATCH_MAX_X = 5170000
SERBIA_PATCH_MAX_Y = 2340000


@click.command()
@click.argument("paths_to_results", nargs=-1)
@click.argument("path_to_countries")
@click.argument("path_to_world")
@click.argument("path_to_boxplot")
@click.argument("path_to_map")
@click.argument("path_to_correlation")
def visualise_normed_potentials(paths_to_results, path_to_countries, path_to_world,
                                path_to_boxplot, path_to_map, path_to_correlation):
    """Visualises the potentials relative to demand in each region.

    Creates:
    * boxplot for each country
    * red/green map
    * plot of correlation of region features to necessary land
    """
    sns.set_context('paper')
    paths_to_results = [paths.split(",") for paths in paths_to_results]
    region_sets = [
        gpd.read_file(paths[0]).to_crs(EPSG_3035_PROJ4).merge(
            pd.concat(
                [pd.read_csv(p).set_index("id") for p in paths[1:]],
                axis=1,
                sort=True
            ).reset_index().rename(columns={"index": "id"}),
            on="id"
        )
        for paths in paths_to_results
    ]
    for region, paths_to_region in zip(region_sets, paths_to_results):
        region["layer_id"] = _infer_layer_id(paths_to_region[0])
    countries = gpd.read_file(path_to_countries).to_crs(EPSG_3035_PROJ4)
    third_countries = _third_countries(countries, gpd.read_file(path_to_world)).to_crs(EPSG_3035_PROJ4)
    _boxplot([region_sets[0], region_sets[-1]], path_to_boxplot)
    _correlation(region_sets, path_to_correlation)
    _map(region_sets[-1], countries, third_countries, path_to_map)


def _boxplot(region_sets, path_to_plot):
    data = pd.concat([pd.DataFrame(gdf) for gdf in region_sets])
    data_eu = data.copy()
    data_eu["country_code"] = "EUR"
    data = pd.concat([data, data_eu])

    fig = plt.figure(figsize=(8, 10))
    ax = fig.add_subplot(111)
    sns.boxplot(
        data=data,
        x="normed_potential",
        y="country_code",
        hue="layer_id",
        order=data.groupby("country_code").normed_potential.quantile(0.75).sort_values().index,
        ax=ax
    )
    ax.set_xlabel("potential relative to demand [-]")
    ax.set_ylabel("country code")
    ax.set_xscale('log')
    ax.axvline(1, color="r", linewidth=0.75)
    fig.savefig(path_to_plot, dpi=300)


def _map(regions, countries, third_countries, path_to_plot):
    winners = regions[regions["normed_potential"] >= 1]
    loosers = regions[regions["normed_potential"] < 1]
    invalids = regions[~regions.isin(pd.concat([winners, loosers]))].dropna()

    fig = plt.figure(figsize=(16, 16))
    ax = fig.add_subplot(111)
    ax.set_aspect('equal')
    ax.add_patch(_serbia_montenegro_patch(regions)) # FIXME, see comment in function below
    third_countries.plot(
        color='grey', edgecolor='black', linewidth=0.4, ax=ax, alpha=0.2
    )
    countries.plot(
        color='white', edgecolor='black', linewidth=0.4, ax=ax
    )
    winners.plot(color=GREEN, linewidth=0.1, ax=ax)
    loosers.plot(color=RED, linewidth=0.1, ax=ax)
    if not invalids.empty:
        invalids.plot(color="grey", linewidth=0.1, ax=ax)
    ax.set_xlim(MAP_MIN_X, MAP_MAX_X)
    ax.set_ylim(MAP_MIN_Y, MAP_MAX_Y)
    ax.set_xticks([])
    ax.set_yticks([])
    fig.savefig(path_to_plot, dpi=300)


def _correlation(region_sets, path_to_plot):
    fig = plt.figure(figsize=(10, 10))
    ax1 = fig.add_subplot(231)
    for region_set in reversed(region_sets):
        layer_id = region_set["layer_id"][0]
        region_set["area_km2"] = area_in_squaremeters(region_set) / 1e6
        sns.regplot(
            data=region_set,
            x="area_km2",
            y="normed_potential",
            label=layer_id,
            fit_reg=False,
            ax=ax1
        )
    ax1.axhline(1, color="r", linewidth=0.75)
    berlin = region_sets[1].set_index("name").loc["Berlin"]
    ax1.plot(
        [berlin.area_km2], [berlin.normed_potential],
        color="red", marker="o", markersize=6
    )
    ax1.text(x=berlin.area_km2 + 500, y=berlin.normed_potential - 0.02, s="Berlin")
    ax1.set_xlabel("region size [km^2]")
    ax1.set_ylabel("potential relative to demand")
    ax1.set_xlim(0.1,)
    ax1.set_ylim(0, 2)
    ax1.set_xscale("log")
    ax1.legend()

    ax2 = fig.add_subplot(232, sharey=ax1)
    for region_set in reversed(region_sets):
        layer_id = region_set["layer_id"][0]
        region_set["population_density"] = region_set["population_sum"] / region_set["area_km2"]
        sns.regplot(
            data=region_set,
            x="population_density",
            y="normed_potential",
            label=layer_id,
            fit_reg=False,
            ax=ax2
        )
    ax2.axhline(1, color="r", linewidth=0.75)
    berlin = region_sets[1].set_index("name").loc["Berlin"]
    ax2.plot(
        [berlin.population_density], [berlin.normed_potential],
        color="red", marker="o", markersize=6
    )
    ax2.text(x=berlin.population_density + 2000, y=berlin.normed_potential - 0.02, s="Berlin")
    ax2.set_ylabel("")
    ax2.set_xlabel("population density [p/km^2]")
    ax2.set_xlim(0.1,)
    ax2.set_ylim(0, 2)
    ax2.set_xscale("log")
    ax2.legend()

    ax3 = fig.add_subplot(233, sharey=ax1)
    for region_set in reversed(region_sets):
        layer_id = region_set["layer_id"][0]
        region_set["protection_share"] = (region_set["pa_{}".format(ProtectedArea.PROTECTED.value)] /
                                          region_set[[f"pa_{cover.value}" for cover in ProtectedArea]].sum(axis=1))
        sns.regplot(
            data=region_set,
            x="protection_share",
            y="normed_potential",
            label=layer_id,
            fit_reg=False,
            ax=ax3
        )
    ax3.axhline(1, color="r", linewidth=0.75)
    berlin = region_sets[1].set_index("name").loc["Berlin"]
    ax3.plot(
        [berlin.protection_share], [berlin.normed_potential],
        color="red", marker="o", markersize=6
    )
    ax3.text(x=berlin.protection_share, y=berlin.normed_potential - 0.02, s="Berlin")
    ax3.set_ylabel("")
    ax3.set_xlabel("share of environmental protection [-]")
    ax3.set_xlim(0, 1.0)
    ax3.set_ylim(0, 2)
    ax3.legend()

    ax4 = fig.add_subplot(234)
    for region_set in reversed(region_sets):
        layer_id = region_set["layer_id"][0]
        total_points = region_set[[f"lc_{cover.value}" for cover in GlobCover]].sum(axis=1)
        farmland_points = region_set[[f"lc_{cover.value}" for cover in FARM]].sum(axis=1)
        region_set["farmland_share"] = farmland_points / total_points
        sns.regplot(
            data=region_set,
            x="farmland_share",
            y="normed_potential",
            label=layer_id,
            fit_reg=False,
            ax=ax4
        )
    ax4.axhline(1, color="r", linewidth=0.75)
    berlin = region_sets[1].set_index("name").loc["Berlin"]
    ax4.plot(
        [berlin.farmland_share], [berlin.normed_potential],
        color="red", marker="o", markersize=6
    )
    ax4.text(x=berlin.farmland_share, y=berlin.normed_potential - 0.02, s="Berlin")
    ax4.set_xlabel("farmland share [-]")
    ax4.set_ylabel("potential relative to demand")
    ax4.set_xlim(0, 1.0)
    ax4.set_ylim(0, 2)
    ax4.legend()

    ax5 = fig.add_subplot(235, sharey=ax4)
    for region_set in reversed(region_sets):
        layer_id = region_set["layer_id"][0]
        total_points = region_set[[f"lc_{cover.value}" for cover in GlobCover]].sum(axis=1)
        forest_points = region_set[[f"lc_{cover.value}" for cover in FOREST]].sum(axis=1)
        region_set["forest_share"] = forest_points / total_points
        sns.regplot(
            data=region_set,
            x="forest_share",
            y="normed_potential",
            label=layer_id,
            fit_reg=False,
            ax=ax5
        )
    ax5.axhline(1, color="r", linewidth=0.75)
    berlin = region_sets[1].set_index("name").loc["Berlin"]
    ax5.plot(
        [berlin.forest_share], [berlin.normed_potential],
        color="red", marker="o", markersize=6
    )
    ax5.text(x=berlin.forest_share, y=berlin.normed_potential - 0.02, s="Berlin")
    ax5.set_ylabel("")
    ax5.set_xlabel("forest share [-]")
    ax5.set_xlim(0, 1.0)
    ax5.set_ylim(0, 2)
    ax5.legend()

    ax6 = fig.add_subplot(236, sharey=ax4)
    for region_set in reversed(region_sets):
        layer_id = region_set["layer_id"][0]
        sns.regplot(
            data=region_set,
            x="industrial_demand_fraction",
            y="normed_potential",
            label=layer_id,
            fit_reg=False,
            ax=ax6
        )
    ax6.axhline(1, color="r", linewidth=0.75)
    berlin = region_sets[1].set_index("name").loc["Berlin"]
    ax6.plot(
        [berlin.industrial_demand_fraction], [berlin.normed_potential],
        color="red", marker="o", markersize=6
    )
    ax6.text(x=berlin.industrial_demand_fraction, y=berlin.normed_potential - 0.02, s="Berlin")
    ax6.set_ylabel("")
    ax6.set_xlabel("share of industrial demand [-]")
    ax6.set_xlim(0, 1.0)
    ax6.set_ylim(0, 2)
    ax6.legend()

    fig.tight_layout()
    fig.savefig(path_to_plot, dpi=300)


def _third_countries(countries, world):
    return world[~world.ISO_A3.isin(countries.country_code.unique())]


def _infer_layer_id(path_to_regions):
    # based on the idea, that paths are something like 'build/adm2/blabla.geojson'
    # FIXME should be a more robust approach
    return path_to_regions.split("/")[1]


def _serbia_montenegro_patch(regions):
    # FIXME this patches the issue of currently having a gap between Serbia (NUTS/LAU)
    # and Montenegro (GADM) which is clearly visible in the final plot. I believe the
    # issue stems from the fact that the demarcation process hasn't been finished --
    # at least not back in 2013 where the NUTS/LAU data stems from. See for example:
    # http://www.bezbednost.org/upload/document/1112231512_pp_3_territorial_an.pdf
    # The issue might be solved with the current 2016 NUTS/LAU data, but that data
    # set hasn't been published by EuroStat so far.
    coords = ((SERBIA_PATCH_MIN_X, SERBIA_PATCH_MIN_Y), (SERBIA_PATCH_MIN_X, SERBIA_PATCH_MAX_Y),
              (SERBIA_PATCH_MAX_X, SERBIA_PATCH_MAX_Y), (SERBIA_PATCH_MAX_X, SERBIA_PATCH_MIN_Y),
              (SERBIA_PATCH_MIN_X, SERBIA_PATCH_MIN_Y))
    patch = shapely.geometry.Polygon(coords)
    for region in regions[regions.country_code.isin(["MNE", "SRB", "ALB"])].geometry:
        patch = patch - region
    return PolygonPatch(patch, linewidth=0.0, facecolor=GREEN)


if __name__ == "__main__":
    visualise_normed_potentials()
