"""Visualise the exclusion layers defining land eligibility."""
import click
import numpy as np
import fiona
import rasterio
from rasterio.plot import show
from descartes import PolygonPatch
import shapely.geometry
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
import seaborn as sns

from src.technical_eligibility import FARM, FOREST, VEGETATION, BARE
from src.potentials import ProtectedArea
from src.vis import GREEN, BLUE, RED

YELLOW = "#FABC3C"


@click.command()
@click.argument("path_to_shapes")
@click.argument("path_to_land_cover")
@click.argument("path_to_slope")
@click.argument("path_to_protected_areas")
@click.argument("path_to_settlements")
@click.argument("path_to_output")
@click.argument("country_code")
def exclusion_layers(path_to_shapes, path_to_land_cover, path_to_slope, path_to_protected_areas,
                     path_to_settlements, path_to_output, country_code):
    """Visualise the exclusion layers defining land eligibility."""
    with fiona.open(path_to_shapes, "r") as shapefile:
        shape = [feature["geometry"] for feature in shapefile
                 if feature["properties"]["country_code"] == country_code][0]
    x_min, y_min, x_max, y_max = shapely.geometry.asShape(shape).bounds
    land_cover, slope, protected_areas, esm = _read_raster(
        x_min, y_min, x_max, y_max,
        path_to_land_cover,
        path_to_slope,
        path_to_protected_areas,
        path_to_settlements

    )
    fig = plt.figure(figsize=(10, 5.5), frameon=False, constrained_layout=True)
    ax1 = fig.add_subplot(221)
    show(land_cover, extent=(x_min, x_max, y_min, y_max), ax=ax1,
         cmap=ListedColormap(sns.light_palette(sns.desaturate(BLUE, 0.85)).as_hex()))
    ax1.set_title("Exclusion from land cover")
    ax2 = fig.add_subplot(222)
    show(slope, extent=(x_min, x_max, y_min, y_max), ax=ax2,
         cmap=ListedColormap(sns.light_palette(sns.desaturate(YELLOW, 0.85)).as_hex()))
    ax2.set_title("Exclusion from slope")
    ax3 = fig.add_subplot(223)
    show(protected_areas, extent=(x_min, x_max, y_min, y_max), ax=ax3,
         cmap=ListedColormap(sns.light_palette(sns.desaturate(GREEN, 0.85)).as_hex()))
    ax3.set_title("Exclusion from protected areas")
    ax4 = fig.add_subplot(224)
    show(esm, extent=(x_min, x_max, y_min, y_max), ax=ax4,
         cmap=ListedColormap(sns.light_palette(sns.desaturate(RED, 0.85)).as_hex()))
    ax4.set_title("Exclusion from urban settlements")
    for ax in [ax1, ax2, ax3, ax4]:
        ax.add_patch(_inverted_shape(shape))
        ax.set_xticks([])
        ax.set_yticks([])
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["bottom"].set_visible(False)
        ax.spines["left"].set_visible(False)
    fig.set_constrained_layout_pads(hspace=0.1, wspace=0.1)
    fig.savefig(path_to_output, dpi=300, transparent=True)
    _add_alpha_mask(path_to_output)


def _read_raster(x_min, y_min, x_max, y_max, path_to_land_cover, path_to_slope,
                 path_to_protected_areas, path_to_settlements):
    with rasterio.open(path_to_settlements, "r") as src:
        all_points = [src.index(x[0], x[1]) for x in [(x_min, y_min), (x_min, y_max), (x_max, y_min), (x_max, y_max)]]
        x_min = min(x[0] for x in all_points)
        x_max = max(x[0] for x in all_points)
        y_min = min(x[1] for x in all_points)
        y_max = max(x[1] for x in all_points)
        data = src.read(1)
        data = data[slice(x_min, x_max), slice(y_min, y_max)]
        esm = np.zeros_like(data, dtype=np.uint8)
        esm[data > 0.01] = 1
    with rasterio.open(path_to_slope, "r") as src:
        data = src.read(1)
        data = data[slice(x_min, x_max), slice(y_min, y_max)]
        slope = np.zeros_like(data, dtype=np.uint8)
        slope[data > 20] = 1
    with rasterio.open(path_to_protected_areas, "r") as src:
        data = src.read(1)
        data = data[slice(x_min, x_max), slice(y_min, y_max)]
        protected_areas = np.zeros_like(data, dtype=np.uint8)
        protected_areas[data == ProtectedArea.PROTECTED] = 1
    with rasterio.open(path_to_land_cover, "r") as src:
        data = src.read(1)
        data = data[slice(x_min, x_max), slice(y_min, y_max)]
        land_cover = np.zeros_like(data, dtype=np.uint8)
        eligible_for_wind = FARM + FOREST + VEGETATION + BARE
        land_cover[~np.isin(data, eligible_for_wind)] = 1
    return land_cover, slope, protected_areas, esm


def _inverted_shape(shape):
    shape = shapely.geometry.asShape(shape)
    x_min, y_min, x_max, y_max = shape.bounds
    coords = ((x_min - 1, y_min - 1), (x_min - 1, y_max + 1),
              (x_max + 1, y_max + 1), (x_max + 1, y_min - 1),
              (x_min - 1, y_min - 1))
    patch = shapely.geometry.Polygon(coords)
    patch = patch - shape
    return PolygonPatch(patch, edgecolor="k", facecolor="w")


def _add_alpha_mask(path_to_output):
    # removing the white areas from the inverted shape
    img = mpl.image.imread(path_to_output)
    white_parts = (img[:, :, 0] == 1) & (img[:, :, 1] == 1) & (img[:, :, 2] == 1)
    img[white_parts] = [1, 1, 1, 0]
    mpl.image.imsave(path_to_output, img, dpi=300)


if __name__ == "__main__":
    exclusion_layers()
