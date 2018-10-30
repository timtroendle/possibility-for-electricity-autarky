from pathlib import Path
from itertools import chain, repeat

import click
import pandas as pd
import geopandas as gpd
import matplotlib
import matplotlib.pyplot as plt
import seaborn as sns

from src.vis.potentials_normed import MAP_MIN_X, MAP_MAX_X, MAP_MIN_Y, MAP_MAX_Y, EPSG_3035_PROJ4, RED

PV_SHARE = 0.6
PATH_TO_FONT_AWESOME = Path(__file__).parent / 'fonts' / 'fa-solid-900.ttf'
LAYER_UNICODE = "\uf5fd"
AREA_UNICODE = "\uf0ac"


@click.command()
@click.argument("paths_to_units_and_fraction_land_necessary_and_population", nargs=-1)
@click.argument("path_to_output")
def necessary_land_map(paths_to_units_and_fraction_land_necessary_and_population, path_to_output):
    sns.set_context('paper')
    assert len(paths_to_units_and_fraction_land_necessary_and_population) % 3 == 0
    number_units = int(len(paths_to_units_and_fraction_land_necessary_and_population) / 3)
    unit_layers = [
        gpd.read_file(path).to_crs(EPSG_3035_PROJ4)
        for path in paths_to_units_and_fraction_land_necessary_and_population[0:number_units]
    ]
    fractions_necessary_land_layers = [
        pd.read_csv(path)
        for path in paths_to_units_and_fraction_land_necessary_and_population[number_units:2 * number_units]
    ]
    pops = [
        pd.read_csv(path)
        for path in paths_to_units_and_fraction_land_necessary_and_population[2 * number_units:]
    ]
    unit_layers = [units.merge(fractions_necessary_land, on="id", how="left").merge(pop, on="id", how="left")
                   for units, fractions_necessary_land, pop in zip(unit_layers, fractions_necessary_land_layers, pops)]
    layer_names = [
        _layer_name(path_to_results)
        for path_to_results in paths_to_units_and_fraction_land_necessary_and_population[0:number_units]
    ]
    layer_names = [
        name.capitalize()
        for name in layer_names
    ]
    _map(unit_layers, layer_names, path_to_output)


def _map(unit_layers, layer_names, path_to_plot):
    fig = plt.figure(figsize=(8, 8), constrained_layout=True)
    axes = fig.subplots(2, 2).flatten()
    norm = matplotlib.colors.Normalize(vmin=0, vmax=1)
    cmap = sns.light_palette(sns.desaturate(RED, 0.85), reverse=False, as_cmap=True)
    _plot_layer(unit_layers[0], layer_names[0], norm, cmap, axes[0])
    _plot_layer(unit_layers[1], layer_names[1], norm, cmap, axes[1])
    _plot_layer(unit_layers[2], layer_names[2], norm, cmap, axes[2])
    _plot_layer(unit_layers[3], layer_names[3], norm, cmap, axes[3])

    _plot_colorbar(fig, axes, norm, cmap)
    fig.savefig(path_to_plot, dpi=300, transparent=True)


def _plot_layer(units, layer_name, norm, cmap, ax):
    ax.set_aspect('equal')
    units.plot(
        linewidth=0.1,
        column="fraction_non_built_up_land_necessary",
        vmin=norm.vmin,
        vmax=norm.vmax,
        cmap=cmap,
        ax=ax
    )
    ax.set_xlim(MAP_MIN_X, MAP_MAX_X)
    ax.set_ylim(MAP_MIN_Y, MAP_MAX_Y)
    ax.set_xticks([])
    ax.set_yticks([])
    sns.despine(ax=ax, top=True, bottom=True, left=True, right=True)

    ax.annotate(
        f"{LAYER_UNICODE} ",
        xy=[0.10, 0.90],
        xycoords='axes fraction',
        fontproperties=matplotlib.font_manager.FontProperties(fname=PATH_TO_FONT_AWESOME.as_posix()),
        color="black"
    )
    ax.annotate(
        f"{AREA_UNICODE} ",
        xy=[0.10, 0.85],
        xycoords='axes fraction',
        fontproperties=matplotlib.font_manager.FontProperties(fname=PATH_TO_FONT_AWESOME.as_posix()),
        color=sns.desaturate(RED, 0.85)
    )
    ax.annotate(layer_name, xy=[0.17, 0.90], xycoords='axes fraction')
    median_land_demand_population_centered = _calculate_population_centered_median_land_demand(units)
    ax.annotate(f"{median_land_demand_population_centered:.0f}%", xy=[0.17, 0.85], xycoords='axes fraction')


def _plot_colorbar(fig, axes, norm, cmap):
    s_m = matplotlib.cm.ScalarMappable(cmap=cmap, norm=norm)
    s_m.set_array([])
    cbar = fig.colorbar(s_m, ax=axes, fraction=1, aspect=35, shrink=0.65)
    cbar.set_ticks(cbar.get_ticks())
    cbar.set_ticklabels(["{:.0f}%".format(tick * 100) if tick < 1 else "≥ 100%"
                         for tick in cbar.get_ticks()])
    cbar.outline.set_linewidth(0)


def _calculate_population_centered_median_land_demand(units):
    return pd.Series(
        data=list(chain(*[
            (repeat(unit[1]["fraction_non_built_up_land_necessary"], round(unit[1].population_sum / 100)))
            for unit in units.iterrows()
        ]))
    ).median() * 100


def _layer_name(path_to_units):
    return path_to_units.split("/")[-2]


if __name__ == "__main__":
    necessary_land_map()
