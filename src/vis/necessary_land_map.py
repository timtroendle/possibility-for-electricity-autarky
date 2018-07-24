import click
import geopandas as gpd
import matplotlib
import matplotlib.pyplot as plt
import seaborn as sns

from src.vis.necessary_land_all_layers import necessary_land_factor
from src.vis.potentials_normed import MAP_MIN_X, MAP_MAX_X, MAP_MIN_Y, MAP_MAX_Y, EPSG_3035_PROJ4, GREEN

PV_SHARE = 0.5


@click.command()
@click.argument("paths_to_regions", nargs=-1)
@click.argument("path_to_output")
def necessary_land_map(paths_to_regions, path_to_output):
    sns.set_context('paper')
    region_layers = [
        gpd.read_file(path_to_regions).to_crs(EPSG_3035_PROJ4).merge(
            necessary_land_factor(PV_SHARE, _layer_name(path_to_regions)),
            on="id",
            how="left"
        )
        for path_to_regions in paths_to_regions
    ]
    countries = gpd.read_file("build/worldwide-countries.geojson").to_crs(EPSG_3035_PROJ4)
    _map(region_layers, countries, path_to_output)


def _map(region_layers, countries, path_to_plot):
    fig = plt.figure(figsize=(8, 8))
    gs = matplotlib.gridspec.GridSpec(2, 3, width_ratios=[5, 5, 1])
    norm = matplotlib.colors.Normalize(vmin=0, vmax=1)
    cmap = sns.light_palette(GREEN, reverse=False, as_cmap=True)
    _plot_layer(region_layers[0], countries, "(a)", norm, cmap, fig.add_subplot(gs[0]))
    _plot_layer(region_layers[1], countries, "(b)", norm, cmap, fig.add_subplot(gs[1]))
    _plot_layer(region_layers[2], countries, "(c)", norm, cmap, fig.add_subplot(gs[3]))
    _plot_layer(region_layers[3], countries, "(d)", norm, cmap, fig.add_subplot(gs[4]))

    fig.tight_layout()
    _plot_colorbar(fig, gs, norm, cmap)
    fig.savefig(path_to_plot, dpi=300)


def _plot_layer(regions, countries, annotation, norm, cmap, ax):
    ax.set_aspect('equal')
    regions.plot(linewidth=0.1, column="fraction land necessary", vmin=norm.vmin, vmax=norm.vmax, cmap=cmap, ax=ax)
    ax.set_xlim(MAP_MIN_X, MAP_MAX_X)
    ax.set_ylim(MAP_MIN_Y, MAP_MAX_Y)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["bottom"].set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.annotate(annotation, xy=[0.10, 0.85], xycoords='axes fraction')


def _plot_colorbar(fig, gs, norm, cmap):
    s_m = matplotlib.cm.ScalarMappable(cmap=cmap, norm=norm)
    s_m.set_array([])
    ax2 = fig.add_subplot(gs[2])
    ax5 = fig.add_subplot(gs[5])
    ax2.axis("off")
    ax5.axis("off")
    cbar = fig.colorbar(s_m, ax=[ax2, ax5], fraction=1, aspect=35, shrink=0.65)
    cbar.set_ticks(cbar.get_ticks())
    cbar.set_ticklabels(["{:.0f}%".format(tick * 100) for tick in cbar.get_ticks()])
    cbar.outline.set_linewidth(0)


def _layer_name(path_to_regions):
    return path_to_regions.split("/")[-2]


if __name__ == "__main__":
    necessary_land_map()
