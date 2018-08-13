import click
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import seaborn as sns

from src.vis.potentials_normed import MAP_MIN_X, MAP_MAX_X, MAP_MIN_Y, MAP_MAX_Y, EPSG_3035_PROJ4, \
    GREEN, RED


@click.command()
@click.argument("paths_to_results", nargs=-1)
@click.argument("path_to_output")
def necessary_land_map(paths_to_results, path_to_output):
    sns.set_context('paper')
    unit_layers = [
        gpd.read_file(path_to_results).to_crs(EPSG_3035_PROJ4)
        for path_to_results in paths_to_results
    ]
    _map(unit_layers, path_to_output)


def _map(unit_layers, path_to_plot):
    fig = plt.figure(figsize=(8, 8), constrained_layout=True)
    axes = fig.subplots(2, 2).flatten()
    fig.subplots_adjust(left=0, right=1.0, bottom=0.0, top=1.0, wspace=0.0, hspace=0.0)
    _plot_layer(unit_layers[0], "(a)", axes[0], linewidth=0.0)
    _plot_layer(unit_layers[1], "(b)", axes[1], linewidth=0.2)
    _plot_layer(unit_layers[2], "(c)", axes[2], linewidth=0.12)
    _plot_layer(unit_layers[3], "(d)", axes[3], linewidth=0.025)

    fig.savefig(path_to_plot, dpi=300)


def _plot_layer(units, annotation, ax, linewidth=0.1):
    winners = units[units["normed_potential"] >= 1]
    loosers = units[units["normed_potential"] < 1]
    invalids = units[~units.isin(pd.concat([winners, loosers]))].dropna()

    ax.set_aspect('equal')
    winners.plot(color=sns.desaturate(GREEN, 0.85), linewidth=linewidth, edgecolor="white", alpha=0.5, ax=ax)
    if not loosers.empty:
        loosers.plot(color=RED, linewidth=0.1, ax=ax)
    if not invalids.empty:
        invalids.plot(color="grey", linewidth=0.1, ax=ax)
    ax.set_xlim(MAP_MIN_X, MAP_MAX_X)
    ax.set_ylim(MAP_MIN_Y, MAP_MAX_Y)
    ax.set_xticks([])
    ax.set_yticks([])
    sns.despine(ax=ax, top=True, bottom=True, left=True, right=True)
    ax.annotate(annotation, xy=[0.10, 0.85], xycoords='axes fraction')


def _layer_name(path_to_units):
    return path_to_units.split("/")[-2]


if __name__ == "__main__":
    necessary_land_map()
