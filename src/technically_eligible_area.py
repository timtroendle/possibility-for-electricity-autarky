"""Determines area of technically eligible land for renewables."""
import math

import click
import numpy as np
import rasterio

from src.technical_eligibility import Eligibility

DATATYPE = np.float32


@click.command()
@click.argument("path_to_eligibility_categories")
@click.argument("path_to_building_share")
@click.argument("path_to_rooftop_correction_factor")
@click.argument("path_to_result")
def determine_area(path_to_eligibility_categories, path_to_building_share,
                   path_to_rooftop_correction_factor, path_to_result):
    """Determines area of technically eligible land for renewables.

    For all eligibility categories other than rooftop PV, this is simply the pixel/cell size.
    For rooftop PV, we reduce the area to the building footprints, and we furthermore apply a
    correction factor to map from building footprint to available rooftop space.
    """
    with rasterio.open(path_to_eligibility_categories) as src:
        eligibility_categories = src.read(1)
        meta = src.meta
        bounds = src.bounds
        resolution = src.res[0]
    pixel_area = determine_pixel_areas(meta, bounds, resolution)
    areas_of_eligibility = pixel_area.copy()
    rooftop_area = determine_rooftop_areas(pixel_area, path_to_building_share, path_to_rooftop_correction_factor)
    pv_rooftop_mask = eligibility_categories == Eligibility.ROOFTOP_PV
    areas_of_eligibility[pv_rooftop_mask] = rooftop_area[pv_rooftop_mask]
    write_to_file(areas_of_eligibility, path_to_result, meta)


def determine_pixel_areas(meta, bounds, resolution):
    """Returns a raster in which the value corresponds to the area of the pixel."""
    # the following is based on https://gis.stackexchange.com/a/288034/77760
    # and assumes the data to be in WGS84
    assert meta["crs"] == rasterio.crs.CRS.from_epsg("4326") # WGS84
    latitudes = np.linspace(
        start=bounds.top,
        stop=bounds.bottom,
        num=meta["height"],
        endpoint=True,
        dtype=DATATYPE
    )
    varea_of_pixel = np.vectorize(lambda lat: area_of_pixel(resolution, lat))
    pixel_area = varea_of_pixel(latitudes) # vector
    return pixel_area.repeat(meta["width"]).reshape(meta["height"], meta["width"]).astype(DATATYPE)


def area_of_pixel(pixel_size, center_lat):
    """Calculate km^2 area of a wgs84 square pixel.

    Adapted from: https://gis.stackexchange.com/a/127327/2397

    Parameters:
        pixel_size (float): length of side of pixel in degrees.
        center_lat (float): latitude of the center of the pixel. Note this
            value +/- half the `pixel-size` must not exceed 90/-90 degrees
            latitude or an invalid area will be calculated.

    Returns:
        Area of square pixel of side length `pixel_size` centered at
        `center_lat` in km^2.

    """
    a = 6378137  # meters
    b = 6356752.3142  # meters
    e = math.sqrt(1 - (b / a)**2)
    area_list = []
    for f in [center_lat + pixel_size / 2, center_lat - pixel_size / 2]:
        zm = 1 - e * math.sin(math.radians(f))
        zp = 1 + e * math.sin(math.radians(f))
        area_list.append(
            math.pi * b**2 * (
                math.log(zp / zm) / (2 * e) +
                math.sin(math.radians(f)) / (zp * zm)))
    return pixel_size / 360. * (area_list[0] - area_list[1]) / 1e6


def determine_rooftop_areas(pixel_areas, path_to_building_share, path_to_rooftop_correction_factor):
    """Returns a raster in which the value corresponds to the rooftop area in the pixel."""
    with rasterio.open(path_to_building_share) as f_building_share, \
            open(path_to_rooftop_correction_factor, "r") as f_factor:
        factor = float(f_factor.readline())
        building_share = f_building_share.read(1)
    return pixel_areas * building_share * factor


def write_to_file(areas_of_eligibility, path_to_result, meta):
    meta.update(dtype=DATATYPE)
    if "transform" in meta.keys():
        del meta["transform"] # this is to avoid a deprecation warning of rasterio < 1.0
    with rasterio.open(path_to_result, 'w', **meta) as new_geotiff:
        new_geotiff.write(areas_of_eligibility, 1)


if __name__ == "__main__":
    determine_area()
