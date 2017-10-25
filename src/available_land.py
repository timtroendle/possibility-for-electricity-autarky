"""This module determines available land for renewable generation based on geospatial data."""
from enum import IntEnum
from operator import add
from functools import reduce
from pathlib import Path

import click
import geopandas as gpd
from rasterstats import zonal_stats


class GlobCoverCategory(IntEnum):
    """Original categories taken from GlobCover 2009 land cover."""
    POST_FLOODING = 11
    RAINFED_CROPLANDS = 14
    MOSAIC_CROPLAND = 20
    MOSAIC_VEGETATION = 30
    CLOSED_TO_OPEN_BROADLEAVED_FOREST = 40
    CLOSED_BROADLEAVED_FOREST = 50
    OPEN_BROADLEAVED_FOREST = 60
    CLOSED_NEEDLELEAVED_FOREST = 70
    OPEN_NEEDLELEAVED_FOREST = 90
    CLOSED_TO_OPEN_MIXED_FOREST = 100
    MOSAIC_FOREST = 110
    MOSAIC_GRASSLAND = 120
    CLOSED_TO_OPEN_SHRUBLAND = 130
    CLOSED_TO_OPEN_HERBS = 140
    SPARSE_VEGETATION = 150
    CLOSED_TO_OPEN_REGULARLY_FLOODED_FOREST = 160
    CLOSED_REGULARLY_FLOODED_FOREST = 170
    CLOSED_TO_OPEN_REGULARLY_FLOODED_GRASSLAND = 180
    ARTIFICAL_SURFACES_AND_URBAN_AREAS = 190
    BARE_AREAS = 200
    WATER_BODIES = 210
    PERMANENT_SNOW = 220
    NO_DATA = 230


class LandCoverCategory(IntEnum):
    """Simplified land cover categories used in this study.

    The mapping from GlobCover is done in LAND_COVER_MAP.
    """
    WATER = 1
    NO_WATER = 2
    NO_DATA = 3


LAND_COVER_MAP = {
    GlobCoverCategory.POST_FLOODING: LandCoverCategory.NO_WATER,
    GlobCoverCategory.RAINFED_CROPLANDS: LandCoverCategory.NO_WATER,
    GlobCoverCategory.MOSAIC_CROPLAND: LandCoverCategory.NO_WATER,
    GlobCoverCategory.MOSAIC_VEGETATION: LandCoverCategory.NO_WATER,
    GlobCoverCategory.CLOSED_TO_OPEN_BROADLEAVED_FOREST: LandCoverCategory.NO_WATER,
    GlobCoverCategory.CLOSED_BROADLEAVED_FOREST: LandCoverCategory.NO_WATER,
    GlobCoverCategory.OPEN_BROADLEAVED_FOREST: LandCoverCategory.NO_WATER,
    GlobCoverCategory.CLOSED_NEEDLELEAVED_FOREST: LandCoverCategory.NO_WATER,
    GlobCoverCategory.OPEN_NEEDLELEAVED_FOREST: LandCoverCategory.NO_WATER,
    GlobCoverCategory.CLOSED_TO_OPEN_MIXED_FOREST: LandCoverCategory.NO_WATER,
    GlobCoverCategory.MOSAIC_FOREST: LandCoverCategory.NO_WATER,
    GlobCoverCategory.MOSAIC_GRASSLAND: LandCoverCategory.NO_WATER,
    GlobCoverCategory.CLOSED_TO_OPEN_SHRUBLAND: LandCoverCategory.NO_WATER,
    GlobCoverCategory.CLOSED_TO_OPEN_HERBS: LandCoverCategory.NO_WATER,
    GlobCoverCategory.SPARSE_VEGETATION: LandCoverCategory.NO_WATER,
    GlobCoverCategory.CLOSED_TO_OPEN_REGULARLY_FLOODED_FOREST: LandCoverCategory.WATER,
    GlobCoverCategory.CLOSED_REGULARLY_FLOODED_FOREST: LandCoverCategory.WATER,
    GlobCoverCategory.CLOSED_TO_OPEN_REGULARLY_FLOODED_GRASSLAND: LandCoverCategory.WATER,
    GlobCoverCategory.ARTIFICAL_SURFACES_AND_URBAN_AREAS: LandCoverCategory.NO_WATER,
    GlobCoverCategory.BARE_AREAS: LandCoverCategory.NO_WATER,
    GlobCoverCategory.WATER_BODIES: LandCoverCategory.WATER,
    GlobCoverCategory.PERMANENT_SNOW: LandCoverCategory.NO_WATER,
    GlobCoverCategory.NO_DATA: LandCoverCategory.NO_DATA
}


@click.command()
@click.argument("path_to_shp")
@click.argument("path_to_land_cover")
@click.argument("path_to_result")
def determine_available_land(path_to_shp, path_to_land_cover, path_to_result):
    """Quantifies the amount of available land per region based on land cover data."""
    regions = gpd.read_file(path_to_shp)
    stats = zonal_stats(
        regions,
        str(path_to_land_cover),
        categorical=True
    )
    stats = aggregate_stats(stats)
    for cat, values in stats.items():
        regions[cat] = values
    if Path(path_to_result).exists():
        Path(path_to_result).unlink()
    regions.to_file(path_to_result, driver="GeoJSON")


def _mapadd(list1, list2):
    # adds two lists element-wise
    return map(add, list1, list2)


def aggregate_stats(stats):
    """Takes statistics for GlobCover dataset and reduces its categories.

    * Sums all globcover categories that correspond to the same land cover category.
    *

    Example input (from rasterstats):
        [{11: 3, 14: 6, 230: 10}, {14: 7, 230: 14}]
    Corresponding output:
        {
            LandCoverCategory.WATER: [0, 0],
            LandCoverCategory.NO_WATER: [9, 7],
            LandCoverCategory.NO_DATA: [10, 14]
        }
    """
    category_counts = {
        GlobCoverCategory(key): [x[key] if key in x else 0 for x in stats]
        for key in stats[0].keys()
    }
    return {
        cat.name: list(reduce(_mapadd, [values for key, values in category_counts.items()
                                        if LAND_COVER_MAP[key] == cat], [0] * len(stats)))
        for cat in LandCoverCategory
    }


if __name__ == "__main__":
    determine_available_land()
