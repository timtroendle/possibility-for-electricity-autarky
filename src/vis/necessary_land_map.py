import click
import pandas as pd
import geopandas as gpd
import matplotlib
import matplotlib.pyplot as plt
import seaborn as sns

from src.vis.potentials_normed import MAP_MIN_X, MAP_MAX_X, MAP_MIN_Y, MAP_MAX_Y, EPSG_3035_PROJ4, GREEN

PV_SHARE = 0.6


@click.command()
@click.argument("paths_to_units_and_fraction_land_necessary", nargs=-1)
@click.argument("path_to_output")
def necessary_land_map(paths_to_units_and_fraction_land_necessary, path_to_output):
    sns.set_context('paper')
    assert len(paths_to_units_and_fraction_land_necessary) % 2 == 0
    number_units = int(len(paths_to_units_and_fraction_land_necessary) / 2)
    unit_layers = [gpd.read_file(path).to_crs(EPSG_3035_PROJ4)
                   for path in paths_to_units_and_fraction_land_necessary[0:number_units]]
    fractions_necessary_land_layers = [pd.read_csv(path)
                                       for path in paths_to_units_and_fraction_land_necessary[number_units:]]
    unit_layers = [units.merge(fractions_necessary_land, on="id", how="left")
                   for units, fractions_necessary_land in zip(unit_layers, fractions_necessary_land_layers)]
    unit_layers = [units.merge(pd.DataFrame(data={"id": units.id, "layer": _layer_name(path)}),
                               on="id", how="left")
                   for units, path in zip(unit_layers, paths_to_units_and_fraction_land_necessary[0::2])]
    _map(unit_layers, path_to_output)


def _map(unit_layers, path_to_plot):
    fig = plt.figure(figsize=(8, 8), constrained_layout=True)
    axes = fig.subplots(2, 2).flatten()
    norm = matplotlib.colors.Normalize(vmin=0, vmax=1)
    cmap = sns.light_palette(sns.desaturate(GREEN, 0.85), reverse=False, as_cmap=True)
    _plot_layer(unit_layers[0], "(a)", norm, cmap, axes[0])
    _plot_layer(unit_layers[1], "(b)", norm, cmap, axes[1])
    _plot_layer(unit_layers[2], "(c)", norm, cmap, axes[2])
    _plot_layer(unit_layers[3], "(d)", norm, cmap, axes[3])

    _plot_colorbar(fig, axes, norm, cmap)
    fig.savefig(path_to_plot, dpi=300)


def _plot_layer(units, annotation, norm, cmap, ax):
    ax.set_aspect('equal')
    units.plot(
        linewidth=0.1,
        column="fraction non-built-up land necessary",
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
    ax.annotate(annotation, xy=[0.10, 0.85], xycoords='axes fraction')


def _plot_colorbar(fig, axes, norm, cmap):
    s_m = matplotlib.cm.ScalarMappable(cmap=cmap, norm=norm)
    s_m.set_array([])
    cbar = fig.colorbar(s_m, ax=axes, fraction=1, aspect=35, shrink=0.65)
    cbar.set_ticks(cbar.get_ticks())
    cbar.set_ticklabels(["{:.0f}%".format(tick * 100) for tick in cbar.get_ticks()])
    cbar.outline.set_linewidth(0)


def _layer_name(path_to_units):
    return path_to_units.split("/")[-2]


if __name__ == "__main__":
    necessary_land_map()
