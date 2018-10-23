"""This module determines land eligibility for renewable generation based on geospatial data."""
from enum import IntEnum

import click
import numpy as np
import rasterio

from src.utils import Config

DATATYPE = np.uint8


class Eligibility(IntEnum):
    """Categories defining land eligibility for renewable power."""
    NOT_ELIGIBLE = 0
    ROOFTOP_PV = 250
    ONSHORE_WIND_AND_PV_OTHER = 200
    ONSHORE_WIND_OTHER = 180
    ONSHORE_WIND_FARMLAND = 160
    ONSHORE_WIND_FOREST = 140
    ONSHORE_WIND_AND_PV_FARMLAND = 120
    OFFSHORE_WIND = 110
    ONSHORE_WIND_AND_PV_OTHER_PROTECTED = 100
    ONSHORE_WIND_OTHER_PROTECTED = 80
    ONSHORE_WIND_FARMLAND_PROTECTED = 60
    ONSHORE_WIND_FOREST_PROTECTED = 40
    ONSHORE_WIND_AND_PV_FARMLAND_PROTECTED = 20
    OFFSHORE_WIND_PROTECTED = 10

    @property
    def area_column_name(self):
        return "eligibility_{}_km2".format(self.name.lower())

    @property
    def energy_column_name(self):
        return "eligibility_{}_twh_per_year".format(self.name.lower())

    @staticmethod
    def protected():
        return [
            Eligibility.ONSHORE_WIND_AND_PV_OTHER_PROTECTED,
            Eligibility.ONSHORE_WIND_OTHER_PROTECTED,
            Eligibility.ONSHORE_WIND_FARMLAND_PROTECTED,
            Eligibility.ONSHORE_WIND_FOREST_PROTECTED,
            Eligibility.ONSHORE_WIND_AND_PV_FARMLAND_PROTECTED,
            Eligibility.OFFSHORE_WIND_PROTECTED
        ]


class GlobCover(IntEnum):
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
    CLOSED_TO_OPEN_REGULARLY_FLOODED_FOREST = 160 # doesn't exist in Europe
    CLOSED_REGULARLY_FLOODED_FOREST = 170 # doesn't exist in Europe
    CLOSED_TO_OPEN_REGULARLY_FLOODED_GRASSLAND = 180 # roughly 2.3% of land in Europe
    ARTIFICAL_SURFACES_AND_URBAN_AREAS = 190
    BARE_AREAS = 200
    WATER_BODIES = 210
    PERMANENT_SNOW = 220
    NO_DATA = 230


FARM = [GlobCover.POST_FLOODING, GlobCover.RAINFED_CROPLANDS,
        GlobCover.MOSAIC_CROPLAND, GlobCover.MOSAIC_VEGETATION]
FOREST = [GlobCover.CLOSED_TO_OPEN_BROADLEAVED_FOREST, GlobCover.CLOSED_BROADLEAVED_FOREST,
          GlobCover.OPEN_BROADLEAVED_FOREST, GlobCover.CLOSED_NEEDLELEAVED_FOREST,
          GlobCover.OPEN_NEEDLELEAVED_FOREST, GlobCover.CLOSED_TO_OPEN_MIXED_FOREST,
          GlobCover.MOSAIC_FOREST, GlobCover.CLOSED_TO_OPEN_REGULARLY_FLOODED_FOREST,
          GlobCover.CLOSED_REGULARLY_FLOODED_FOREST]
VEGETATION = [GlobCover.MOSAIC_GRASSLAND, GlobCover.CLOSED_TO_OPEN_SHRUBLAND,
              GlobCover.CLOSED_TO_OPEN_HERBS, GlobCover.SPARSE_VEGETATION,
              GlobCover.CLOSED_TO_OPEN_REGULARLY_FLOODED_GRASSLAND]
BARE = [GlobCover.BARE_AREAS]
URBAN = [GlobCover.ARTIFICAL_SURFACES_AND_URBAN_AREAS]
WATER = [GlobCover.WATER_BODIES]


class ProtectedArea(IntEnum):
    """Derived from UNEP-WCMC data set."""
    PROTECTED = 255
    NOT_PROTECTED = 0


@click.command()
@click.argument("path_to_land_cover")
@click.argument("path_to_protected_areas")
@click.argument("path_to_slope")
@click.argument("path_to_bathymetry")
@click.argument("path_to_building_share")
@click.argument("path_to_urban_green_share")
@click.argument("path_to_result")
@click.argument("config", type=Config())
def determine_eligibility(path_to_land_cover, path_to_protected_areas, path_to_slope,
                          path_to_bathymetry, path_to_building_share, path_to_urban_green_share,
                          path_to_result, config):
    """Determines eligibility of land for renewables."""
    with rasterio.open(path_to_land_cover) as src:
        raster_affine = src.affine
        land_cover = src.read(1)
        crs = src.crs
    with rasterio.open(path_to_slope) as src:
        slope = src.read(1)
    with rasterio.open(path_to_protected_areas) as src:
        protected_areas = src.read(1)
    with rasterio.open(path_to_bathymetry) as src:
        bathymetry = src.read(1)
    with rasterio.open(path_to_building_share) as src:
        building_share = src.read(1)
    with rasterio.open(path_to_urban_green_share) as src:
        urban_green_share = src.read(1)
    eligibility = _determine_eligibility(
        land_cover=land_cover,
        protected_areas=protected_areas,
        slope=slope,
        bathymetry=bathymetry,
        building_share=building_share,
        urban_green_share=urban_green_share,
        config=config
    )
    with rasterio.open(path_to_result, 'w', driver='GTiff', height=eligibility.shape[0],
                       width=eligibility.shape[1], count=1, dtype=DATATYPE,
                       crs=crs, transform=raster_affine) as new_geotiff:
        new_geotiff.write(eligibility, 1)


def _determine_eligibility(land_cover, protected_areas, slope, bathymetry, building_share, urban_green_share, config):
    # parameters
    max_slope_pv = config["parameters"]["max-slope"]["pv"]
    max_slope_wind = config["parameters"]["max-slope"]["wind"]
    max_building_share = config["parameters"]["max-building-share"]
    max_urban_green_share = config["parameters"]["max-urban-green-share"]

    # prepare masks
    settlements = (building_share > max_building_share) | (urban_green_share > max_urban_green_share)
    pv = (slope <= max_slope_pv) & ~settlements
    wind = (slope <= max_slope_wind) & ~settlements
    offshore = np.isin(land_cover, WATER) & (bathymetry > config["parameters"]["max-depth-offshore"]) & ~settlements
    protected = protected_areas == ProtectedArea.PROTECTED
    farm = np.isin(land_cover, FARM)
    forest = np.isin(land_cover, FOREST)
    other = np.isin(land_cover, VEGETATION + BARE)

    # allocate eligibility
    land = np.ones_like(land_cover, dtype=DATATYPE) * Eligibility.NOT_ELIGIBLE
    _add_eligibility(land, Eligibility.ROOFTOP_PV, settlements)
    _add_eligibility(land, Eligibility.ONSHORE_WIND_AND_PV_OTHER, wind & pv & other & ~protected)
    _add_eligibility(land, Eligibility.ONSHORE_WIND_AND_PV_OTHER_PROTECTED, wind & pv & other & protected)
    _add_eligibility(land, Eligibility.ONSHORE_WIND_OTHER, wind & ~pv & other & ~protected)
    _add_eligibility(land, Eligibility.ONSHORE_WIND_OTHER_PROTECTED, wind & ~pv & other & protected)
    _add_eligibility(land, Eligibility.ONSHORE_WIND_FARMLAND, wind & ~pv & farm & ~protected)
    _add_eligibility(land, Eligibility.ONSHORE_WIND_FARMLAND_PROTECTED, wind & ~pv & farm & protected)
    _add_eligibility(land, Eligibility.ONSHORE_WIND_FOREST, wind & forest & ~protected)
    _add_eligibility(land, Eligibility.ONSHORE_WIND_FOREST_PROTECTED, wind & forest & protected)
    _add_eligibility(land, Eligibility.ONSHORE_WIND_AND_PV_FARMLAND, wind & pv & farm & ~protected)
    _add_eligibility(land, Eligibility.ONSHORE_WIND_AND_PV_FARMLAND_PROTECTED, wind & pv & farm & protected)
    _add_eligibility(land, Eligibility.OFFSHORE_WIND, offshore & ~protected)
    _add_eligibility(land, Eligibility.OFFSHORE_WIND_PROTECTED, offshore & protected)
    return land


def _add_eligibility(land, eligibility, mask):
    assert all(land[mask] == Eligibility.NOT_ELIGIBLE), f"Overwriting other eligibility with {eligibility}."
    land[mask] = eligibility


if __name__ == "__main__":
    determine_eligibility()
