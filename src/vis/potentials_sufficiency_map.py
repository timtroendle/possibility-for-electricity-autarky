from pathlib import Path

import click
import pandas as pd
import geopandas as gpd
import matplotlib
import matplotlib.pyplot as plt
import seaborn as sns

from src.vis import RED, MAP_MIN_X, MAP_MAX_X, MAP_MIN_Y, MAP_MAX_Y, EPSG_3035_PROJ4


PATH_TO_FONT_AWESOME = Path(__file__).parent / 'fonts' / 'fa-solid-900.ttf'
LAYER_UNICODE = "\uf5fd"
UNITS_UNICODE = "\uf00a"
POPULATION_UNICODE = "\uf007"
LIGHT_GREEN = "#ACBD9A"


@click.command()
@click.argument("paths_to_results", nargs=-1)
@click.argument("path_to_output")
def necessary_land_map(paths_to_results, path_to_output):
    sns.set_context('paper')
    unit_layers = [
        gpd.read_file(path_to_results).to_crs(EPSG_3035_PROJ4)
        for path_to_results in paths_to_results
    ]
    layer_names = [
        _layer_name(path_to_results)
        for path_to_results in paths_to_results
    ]
    layer_names = [
        name.capitalize()
        for name in layer_names
    ]
    _map(unit_layers, layer_names, path_to_output)


def _map(unit_layers, layer_names, path_to_plot):
    fig = plt.figure(figsize=(8, 8), constrained_layout=True)
    axes = fig.subplots(2, 2).flatten()
    fig.subplots_adjust(left=0, right=1.0, bottom=0.0, top=1.0, wspace=0.0, hspace=0.0)
    _plot_layer(unit_layers[0], layer_names[0], axes[0], linewidth=0.0)
    _plot_layer(unit_layers[1], layer_names[1], axes[1], linewidth=0.1)
    _plot_layer(unit_layers[2], layer_names[2], axes[2], linewidth=0.06)
    _plot_layer(unit_layers[3], layer_names[3], axes[3], linewidth=0.0125)

    if path_to_plot[-3:] == "png":
        fig.savefig(path_to_plot, dpi=600, transparent=False)
    else:
        fig.savefig(path_to_plot, dpi=600, transparent=False, pil_kwargs={"compression": "tiff_lzw"})


def _plot_layer(units, layer_name, ax, linewidth=0.1):
    winners = units[units["normed_potential"] >= 1]
    loosers = units[units["normed_potential"] < 1]
    invalids = units[~units.isin(pd.concat([winners, loosers]))].dropna()

    undersupplied_regions_percent = len(loosers) / len(units) * 100
    undersupplied_population_percent = loosers["population_sum"].sum() / units["population_sum"].sum() * 100

    ax.set_aspect('equal')
    winners.plot(color=LIGHT_GREEN, linewidth=linewidth, edgecolor="white", ax=ax)
    if not loosers.empty:
        loosers.plot(color=RED, linewidth=0.1, ax=ax)
    if not invalids.empty:
        invalids.plot(color="grey", linewidth=0.1, ax=ax)
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
        f"{UNITS_UNICODE} ",
        xy=[0.10, 0.85],
        xycoords='axes fraction',
        fontproperties=matplotlib.font_manager.FontProperties(fname=PATH_TO_FONT_AWESOME.as_posix()),
        color=sns.desaturate(RED, 0.85)
    )
    ax.annotate(
        f"{POPULATION_UNICODE} ",
        xy=[0.10, 0.80],
        xycoords='axes fraction',
        fontproperties=matplotlib.font_manager.FontProperties(fname=PATH_TO_FONT_AWESOME.as_posix()),
        color=sns.desaturate(RED, 0.85)
    )
    ax.annotate(layer_name, xy=[0.17, 0.90], xycoords='axes fraction')
    ax.annotate(f"{undersupplied_regions_percent:.0f}%", xy=[0.17, 0.85], xycoords='axes fraction')
    ax.annotate(f"{undersupplied_population_percent:.0f}%", xy=[0.17, 0.80], xycoords='axes fraction')


def _layer_name(path_to_units):
    return path_to_units.split("/")[-3]


if __name__ == "__main__":
    necessary_land_map()
