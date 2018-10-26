"""Determines area of technically eligible land for renewables."""
import math

import click
import numpy as np
import rasterio

from src.technical_eligibility import Eligibility

DATATYPE = np.float32


@click.command()
@click.argument("path_to_eligibility_categories")
@click.argument("path_to_result")
def determine_area(path_to_eligibility_categories, path_to_result):
    """Determines area of technically eligible land for renewables."""
    with rasterio.open(path_to_eligibility_categories) as src:
        raster_affine = src.affine
        eligibility_categories = src.read(1)
        crs = src.crs
        meta = src.meta
        bounds = src.bounds
        resolution = src.res[0]
    pixel_area = _determine_pixel_areas(meta, bounds, resolution)
    with rasterio.open(path_to_result, 'w', driver='GTiff', height=eligibility_categories.shape[0],
                       width=eligibility_categories.shape[1], count=len(Eligibility), dtype=DATATYPE,
                       crs=crs, transform=raster_affine) as new_geotiff:
        for id, eligibility in enumerate(Eligibility, start=1):
            mask = eligibility_categories == eligibility
            areas_of_eligibility = np.zeros_like(pixel_area, dtype=DATATYPE)
            areas_of_eligibility[mask] = pixel_area[mask]
            new_geotiff.write(areas_of_eligibility, id)


def _determine_pixel_areas(meta, bounds, resolution):
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
    return pixel_area.repeat(meta["width"]).reshape(meta["height"], meta["width"])


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


if __name__ == "__main__":
    determine_area()
